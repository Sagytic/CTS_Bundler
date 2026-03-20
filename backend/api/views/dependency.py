"""Dependency graph and dependency-edges APIs."""
from __future__ import annotations

import datetime
import json
from typing import Any

import requests
from langchain_openai import AzureChatOpenAI
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

import logging

from api.config import (
    azure_openai_api_version,
    azure_openai_endpoint,
    azure_openai_key,
    azure_openai_map_filter_deployment,
    llm_map_filter_max_tokens,
    llm_map_filter_temperature,
)
from api.observability import track_llm_request
from api.prompts.dependency_map import dependency_map_prompt_template
from api.models import DependencySnapshot

_log = logging.getLogger("cts.ai")


class DependencyGraphView(APIView):
    """GET/POST /api/dependency/?target_obj=... Returns nodes and links for graph viz."""

    def get(self, request: Request) -> Response:
        return self._process_graph(request)

    def post(self, request: Request) -> Response:
        return self._process_graph(request)

    def _process_graph(self, request: Request) -> Response:
        target_obj = request.GET.get("target_obj") or (request.data or {}).get("target_obj")
        expand_node = request.GET.get("expand_node") or (request.data or {}).get("expand_node")

        effective_target = (expand_node or target_obj or "").strip().upper()
        if not effective_target:
            return Response(
                {"error": "target_obj 또는 expand_node 파라미터가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_expand_request = bool(expand_node and expand_node.strip())

        direct_deps = DependencySnapshot.objects.filter(source_obj=effective_target)
        backward_deps = DependencySnapshot.objects.filter(target_obj=effective_target)

        if not direct_deps.exists() and not backward_deps.exists():
            return Response(
                {"error": f"[{effective_target}] 오브젝트를 찾을 수 없거나 종속성 데이터가 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        raw_links = set()
        nodes_dict = {}

        def add_node(obj_id, group):
            if obj_id not in nodes_dict:
                nodes_dict[obj_id] = {"id": obj_id, "group": group, "name": obj_id}

        add_node(effective_target, 1)

        z_tables_used = set()
        z_programs_called = set()
        for dep in direct_deps:
            add_node(dep.target_obj, dep.target_group)
            raw_links.add((effective_target, dep.target_obj))
            if dep.target_group == 4 and (dep.target_obj.startswith('Z') or dep.target_obj.startswith('Y')):
                z_tables_used.add(dep.target_obj)
            elif dep.target_group in (2, 3) and (dep.target_obj.startswith('Z') or dep.target_obj.startswith('Y')):
                z_programs_called.add(dep.target_obj)

        for dep in backward_deps:
            add_node(dep.source_obj, 2)
            raw_links.add((dep.source_obj, effective_target))
            if dep.source_obj.startswith('Z') or dep.source_obj.startswith('Y'):
                z_programs_called.add(dep.source_obj)

        max_nodes_initial = 150
        max_links_initial = 320
        if not is_expand_request and len(nodes_dict) <= max_nodes_initial:
            shared_programs = set()
            if z_tables_used:
                shared_deps = DependencySnapshot.objects.filter(target_obj__in=z_tables_used).exclude(source_obj=effective_target)
                for dep in shared_deps:
                    if len(nodes_dict) >= max_nodes_initial:
                        break
                    add_node(dep.source_obj, 2)
                    raw_links.add((dep.source_obj, dep.target_obj))
                    shared_programs.add(dep.source_obj)
            programs_to_expand = shared_programs | z_programs_called
            if programs_to_expand:
                deep_deps = DependencySnapshot.objects.filter(source_obj__in=programs_to_expand)
                for dep in deep_deps:
                    if len(nodes_dict) >= max_nodes_initial or len(raw_links) >= max_links_initial:
                        break
                    if dep.target_obj.startswith('Z') or dep.target_obj.startswith('Y') or dep.target_obj in ('EKKO', 'EKPO', 'MSEG', 'MARA', 'VBAK', 'VBAP', 'BKPF', 'BSEG'):
                        add_node(dep.target_obj, dep.target_group)
                        raw_links.add((dep.source_obj, dep.target_obj))

        raw_links_list = [{"source": s, "target": t} for s, t in raw_links]

        if is_expand_request:
            return Response(
                {
                    "snapshot_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "nodes": list(nodes_dict.values()),
                    "links": raw_links_list,
                    "expand": True,
                    "expand_node": expand_node.strip().upper(),
                },
                status=status.HTTP_200_OK,
            )

        if len(raw_links_list) < 5:
            return Response(
                {
                    "snapshot_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "nodes": list(nodes_dict.values()),
                    "links": raw_links_list,
                },
                status=status.HTTP_200_OK,
            )

        try:
            llm = AzureChatOpenAI(
                azure_deployment=azure_openai_map_filter_deployment(),
                api_version=azure_openai_api_version(),
                azure_endpoint=azure_openai_endpoint(),
                api_key=azure_openai_key(),
                temperature=llm_map_filter_temperature(),
                max_tokens=llm_map_filter_max_tokens(),
            )

            prompt_template = dependency_map_prompt_template()
            chain = prompt_template | llm
            with track_llm_request(
                "dependency_map_filter",
                request=request,
                deployment=azure_openai_map_filter_deployment(),
                target_obj=effective_target,
            ):
                res = chain.invoke({
                    "target_obj": effective_target,
                    "nodes": json.dumps(list(nodes_dict.values())),
                    "links": json.dumps(raw_links_list),
                })

            result_text = res.content.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:-3].strip()
            elif result_text.startswith("```"):
                result_text = result_text[3:-3].strip()

            final_data = json.loads(result_text)

            return Response(
                {
                    "snapshot_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "nodes": final_data.get("nodes", []),
                    "links": final_data.get("links", []),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            _log.warning("dependency_map_filter failed: %s", e, exc_info=True)
            return Response(
                {
                    "snapshot_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "nodes": list(nodes_dict.values()),
                    "links": raw_links_list,
                },
                status=status.HTTP_200_OK,
            )


class SnapshotUpdateView(APIView):
    """GET /api/snapshot/update/. Fetches dependency from SAP and updates DB."""

    def get(self, request: Request) -> Response:
        from api.config import sap_client, sap_http_auth, sap_http_url

        url = sap_http_url()
        user, password = sap_http_auth()
        client = sap_client()
        if not url or not user or not password or not client:
            return Response(
                {"error": "환경변수(.env) 설정이 누락되었습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        sap_url = f"{url.rstrip('/')}?sap-client={client}&action=snapshot"
        try:
            response = requests.get(sap_url, auth=(user, password), timeout=60)
            response.raise_for_status()
            data = response.json()
            dependencies = data.get("dependencies", [])

            if not dependencies:
                return Response(
                    {"error": "SAP에서 데이터를 받지 못했습니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            DependencySnapshot.objects.all().delete()
            new_records = [
                DependencySnapshot(
                    source_obj=item["source"],
                    target_obj=item["target"],
                    target_group=item["group"],
                )
                for item in dependencies
            ]
            DependencySnapshot.objects.bulk_create(new_records, batch_size=5000)

            return Response(
                {"message": "스냅샷 다운로드 및 DB 업데이트 성공!", "total_records": len(new_records)},
                status=status.HTTP_200_OK,
            )
        except requests.exceptions.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        except (KeyError, TypeError, ValueError) as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DependencyEdgesView(APIView):
    """
    REST API for dependency edges (same data as MCP get_dependency_edges).
    GET /api/dependency-edges/?target_obj=ZMMR0030&limit=50
    """

    def get(self, request: Request) -> Response:
        target = (request.GET.get("target_obj") or "").strip().upper()
        if not target:
            return Response(
                {"error": "target_obj 쿼리 파라미터가 필요합니다. 예: ?target_obj=ZMMR0030"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            limit = min(int(request.GET.get("limit", 50)), 100)
        except (TypeError, ValueError):
            limit = 50

        fwd = list(
            DependencySnapshot.objects.filter(source_obj=target).values_list(
                "target_obj", flat=True
            )[:limit]
        )
        bwd = list(
            DependencySnapshot.objects.filter(target_obj=target).values_list(
                "source_obj", flat=True
            )[:limit]
        )
        text = (
            f"{target} → 호출: {', '.join(fwd) or '없음'}\n"
            f"{target} ← 호출당함: {', '.join(bwd) or '없음'}"
        )
        return Response(
            {"target_obj": target, "text": text, "calls": fwd, "called_by": bwd},
            status=status.HTTP_200_OK,
        )
