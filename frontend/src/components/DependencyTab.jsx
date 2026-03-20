import React from 'react';
import ReactFlow, { Background, Controls, MiniMap, MarkerType } from 'reactflow';
import 'reactflow/dist/style.css';
import { api } from '../api/client';
import { keepConnectedToRoot, getLayoutedElements } from '../utils/flowLayout';

const SUGGESTED_OBJECTS = ['ZFIR1010', 'ZMMR0030', 'ZFIR5260', 'ZCOR7700', 'ZSTR0040', 'ZSDR1020', 'ZMMR1100'];

function defaultStyleByGroup(group) {
  switch (group) {
    case 1:
      return { background: '#2b2b2b', borderColor: '#a8cdff', color: '#fff', fontWeight: 'normal' };
    case 2:
      return { background: '#2b2b2b', borderColor: '#a8cdff', color: '#fff', fontWeight: 'normal' };
    case 3:
      return { background: '#4a3728', borderColor: '#ffcda8', color: '#fff', fontWeight: 'normal' };
    case 4:
      return { background: '#3a284a', borderColor: '#cda8ff', color: '#fff', fontWeight: 'normal' };
    default:
      return { background: 'var(--bg-sidebar)', borderColor: 'var(--border-color)', color: '#fff', fontWeight: 'normal' };
  }
}

function applyHighlightToNodes(nodeList, selectedId) {
  const skyBlue = '#a8cdff';
  const white = '#fff';
  const black = '#000';
  return nodeList.map((node) => {
    const group = node.data?.group ?? 2;
    const baseStyle = { borderRadius: '8px', padding: '8px 12px', fontSize: '12px', width: 220, textAlign: 'center', boxShadow: '0 4px 10px rgba(0,0,0,0.5)', cursor: 'pointer' };
    if (node.id === selectedId) {
      return { ...node, style: { ...baseStyle, ...node.style, background: skyBlue, color: black, border: '1px solid ' + white, fontWeight: 'bold', zIndex: 10 } };
    }
    const def = defaultStyleByGroup(group);
    return { ...node, style: { ...baseStyle, ...node.style, background: def.background, color: def.color, border: '1px solid ' + def.borderColor, fontWeight: def.fontWeight, zIndex: 1 } };
  });
}

function rawToFlow(rawNodes, rawLinks, selectedId = null) {
  const flowNodes = (rawNodes || []).map((n) => {
    const isSelected = selectedId && n.id === selectedId;
    let bgColor, borderColor, textColor, fontWeight;
    if (isSelected) {
      bgColor = '#a8cdff';
      borderColor = '#fff';
      textColor = '#000';
      fontWeight = 'bold';
    } else {
      const d = defaultStyleByGroup(n.group);
      bgColor = d.background;
      borderColor = d.borderColor;
      textColor = d.color;
      fontWeight = d.fontWeight;
    }
    return {
      id: n.id,
      data: { label: n.name, group: n.group },
      position: { x: 0, y: 0 },
      style: {
        background: bgColor,
        color: textColor,
        border: `1px solid ${borderColor}`,
        borderRadius: '8px',
        padding: '8px 12px',
        fontSize: '12px',
        fontWeight,
        width: 220,
        textAlign: 'center',
        boxShadow: '0 4px 10px rgba(0,0,0,0.5)',
        zIndex: isSelected ? 10 : 1,
        cursor: 'pointer',
      },
    };
  });
  const flowEdges = (rawLinks || []).map((l, idx) => ({
    id: `e-${l.source}-${l.target}-${idx}`,
    source: l.source,
    target: l.target,
    animated: true,
    style: { stroke: '#a8cdff', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#a8cdff' },
  }));
  return { nodes: flowNodes, edges: flowEdges };
}

export default function DependencyTab({
  targetObj,
  setTargetObj,
  loadingGraph,
  setLoadingGraph,
  expandingNodeId,
  setExpandingNodeId,
  setSelectedNodeId,
  nodes,
  setNodes,
  onNodesChange,
  edges,
  setEdges,
  onEdgesChange,
  nodesRef,
  edgesRef,
  onSnapshotUpdate,
  isSnapshotUpdating,
}) {
  const loadDependencyGraph = async (targetOverride = null) => {
    const searchTarget = typeof targetOverride === 'string' ? targetOverride : targetObj;
    const normalized = (searchTarget || '').trim().toUpperCase();
    if (!normalized) {
      alert('검색할 오브젝트 명을 입력해주세요.');
      return;
    }
    setLoadingGraph(true);
    setNodes([]);
    setEdges([]);
    setSelectedNodeId(normalized);
    try {
      const res = await api.get('/api/dependency/', { params: { target_obj: normalized } });
      const { nodes: rawNodes, edges: rawEdges } = rawToFlow(res.data?.nodes || [], res.data?.links || [], normalized);
      const { nodes: connectedNodes, edges: connectedEdges } = keepConnectedToRoot(rawNodes, rawEdges, normalized);
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(connectedNodes, connectedEdges, 'LR', normalized);
      setNodes(applyHighlightToNodes(layoutedNodes, normalized));
      setEdges(layoutedEdges);
      setTargetObj(normalized);
    } catch {
      alert('종속성 데이터를 불러오는 데 실패했습니다.');
    } finally {
      setLoadingGraph(false);
    }
  };

  const loadDependencyExpand = async (nodeId) => {
    if (!nodeId || expandingNodeId || loadingGraph) return;
    setSelectedNodeId(nodeId);
    setExpandingNodeId(nodeId);
    try {
      const res = await api.get('/api/dependency/', { params: { expand_node: nodeId } });
      const rawNodes = res.data?.nodes || [];
      const rawLinks = res.data?.links || [];
      if (!rawNodes.length && !rawLinks.length) {
        setExpandingNodeId(null);
        return;
      }
      const { nodes: newFlowNodes, edges: newFlowEdges } = rawToFlow(rawNodes, rawLinks, null);
      const prevNodes = nodesRef.current;
      const prevEdges = edgesRef.current;
      const byId = new Map(prevNodes.map((n) => [n.id, n]));
      newFlowNodes.forEach((n) => {
        if (!byId.has(n.id)) byId.set(n.id, { ...n, position: { x: 0, y: 0 } });
      });
      const mergedNodes = Array.from(byId.values());
      const edgeKey = (e) => `${e.source}-${e.target}`;
      const seen = new Set(prevEdges.map(edgeKey));
      const mergedEdges = [...prevEdges];
      newFlowEdges.forEach((e, idx) => {
        if (!seen.has(edgeKey(e))) {
          seen.add(edgeKey(e));
          mergedEdges.push({ ...e, id: `e-${e.source}-${e.target}-${prevEdges.length + idx}` });
        }
      });
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(mergedNodes, mergedEdges, 'LR');
      setNodes(applyHighlightToNodes(layoutedNodes, nodeId));
      setEdges(layoutedEdges);
    } catch {
      alert('해당 노드의 하위 종속성을 불러오지 못했습니다.');
    } finally {
      setExpandingNodeId(null);
    }
  };

  return (
    <div className="analyzer-container" style={{ display: 'flex', flexDirection: 'column', height: '100%', paddingBottom: '20px' }}>
      <h2 style={{ color: '#fff', margin: '0 0 20px 0' }}>오브젝트 종속성 분석 (Where-Used)</h2>
      <div
        style={{
          backgroundColor: 'var(--bg-sidebar)',
          padding: '20px',
          borderRadius: '12px',
          marginBottom: '20px',
          border: '1px solid var(--border-color)',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
          <input
            type="text"
            value={targetObj}
            onChange={(e) => setTargetObj(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && loadDependencyGraph(targetObj)}
            placeholder="분석할 프로그램/클래스/테이블명 입력"
            style={{
              flex: 1,
              padding: '12px 15px',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-main)',
              color: '#fff',
              fontSize: '15px',
            }}
          />
          <button onClick={() => loadDependencyGraph(targetObj)} disabled={loadingGraph} className="analyze-btn">
            {loadingGraph ? '스캔 중...' : '종속성 스캔'}
          </button>
          <button
            onClick={onSnapshotUpdate}
            disabled={isSnapshotUpdating}
            style={{
              backgroundColor: isSnapshotUpdating ? '#444' : 'transparent',
              color: isSnapshotUpdating ? '#888' : '#fff',
              border: '1px solid var(--border-color)',
              padding: '12px 20px',
              borderRadius: '8px',
              cursor: isSnapshotUpdating ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontWeight: 'bold',
              fontSize: '14px',
            }}
          >
            {isSnapshotUpdating ? (
              <>
                <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px', borderColor: '#888', borderTopColor: 'transparent' }}></div>
                DB 갱신 중...
              </>
            ) : (
              '🔄 스냅샷 갱신'
            )}
          </button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>추천 타겟:</span>
          {SUGGESTED_OBJECTS.map((obj, idx) => (
            <div key={idx} className="suggestion-chip" style={{ padding: '6px 12px', fontSize: '12px' }} onClick={() => loadDependencyGraph(obj)}>
              {obj}
            </div>
          ))}
        </div>
      </div>
      <div
        style={{
          flex: 1,
          backgroundColor: '#131314',
          borderRadius: '12px',
          overflow: 'hidden',
          border: '1px solid var(--border-color)',
          position: 'relative',
        }}
      >
        {nodes.length > 0 && (
          <div
            style={{
              position: 'absolute',
              top: 10,
              left: 10,
              zIndex: 5,
              fontSize: 12,
              color: 'var(--text-muted)',
              backgroundColor: 'rgba(0,0,0,0.6)',
              padding: '6px 10px',
              borderRadius: 8,
            }}
          >
            클릭: 해당 오브젝트를 루트로 맵 재로드 · 더블클릭: 노드 기준 하위 종속성 확장. 레벨은 루트에서의 연결 거리(0, 1, 2…)입니다.
          </div>
        )}
        {loadingGraph ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', flexDirection: 'column', gap: '15px' }}>
            <div className="spinner" style={{ width: '40px', height: '40px', borderWidth: '4px' }}></div>
            <div style={{ color: 'var(--accent-color)' }}>{targetObj} 오브젝트의 상하위 호출 관계를 추적 중입니다...</div>
          </div>
        ) : nodes.length > 0 ? (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={(_ev, node) => loadDependencyGraph(node.id)}
            onNodeDoubleClick={(_ev, node) => loadDependencyExpand(node.id)}
            fitView
            attributionPosition="bottom-right"
            minZoom={0.1}
          >
            <Background color="#333" gap={16} />
            <Controls style={{ backgroundColor: '#2b2b2b', fill: '#fff' }} />
            <MiniMap nodeStrokeColor="#a8cdff" nodeColor="#2b2b2b" maskColor="rgba(0, 0, 0, 0.7)" style={{ backgroundColor: '#1e1e1f' }} />
          </ReactFlow>
        ) : (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: 'var(--text-muted)' }}>
            상단에서 오브젝트를 검색하면 전문적인 종속성 다이어그램이 표시됩니다.
          </div>
        )}
      </div>
    </div>
  );
}
