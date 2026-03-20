METHOD if_http_extension~handle_request.

    " =================================================================
    " 0. 통합 선언부
    " =================================================================
    DATA: lv_action     TYPE string,
          lv_json       TYPE string,
          lv_user_id    TYPE string,
          lv_target_obj TYPE string,
          lv_timestamp  TYPE char10,
          lv_obj_name   TYPE progname,          " 소스코드 조회용 프로그램명
          lt_source     TYPE TABLE OF string, " 소스코드 라인 테이블
          lv_source     TYPE string.          " JSON으로 변환할 소스 문자열

    TYPES: BEGIN OF ty_node,
             id    TYPE string,
             group TYPE i,
             name  TYPE string,
           END OF ty_node.

    TYPES: BEGIN OF ty_link,
             source TYPE string,
             target TYPE string,
           END OF ty_link.

    TYPES: BEGIN OF ty_graph,
             snapshot_time TYPE string,
             nodes         TYPE STANDARD TABLE OF ty_node WITH DEFAULT KEY,
             links         TYPE STANDARD TABLE OF ty_link WITH DEFAULT KEY,
           END OF ty_graph.

    " 실행 객체 조회를 위한 임시 테이블 타입 (CORRESPONDING 에러 방지)
    TYPES: BEGIN OF ty_logic_link,
             source TYPE string,
             target TYPE string,
           END OF ty_logic_link.

    DATA: ls_graph        TYPE ty_graph,
          lt_nodes        TYPE STANDARD TABLE OF ty_node WITH DEFAULT KEY,
          lt_links        TYPE STANDARD TABLE OF ty_link WITH DEFAULT KEY,
          lt_all_trkorr   TYPE TABLE OF e070-trkorr,
          lt_logic_links  TYPE TABLE OF ty_logic_link.

    TYPES: BEGIN OF ty_tr_deep,
             trkorr     TYPE e070-trkorr,
             trfunction TYPE e070-trfunction,
             trstatus   TYPE e070-trstatus,
             as4user    TYPE e070-as4user,
             as4date    TYPE e070-as4date,
             as4time    TYPE e070-as4time,
             strkorr    TYPE e070-strkorr,
             as4text    TYPE e07t-as4text,
             objects    TYPE STANDARD TABLE OF e071 WITH DEFAULT KEY,
             keys       TYPE STANDARD TABLE OF e071k WITH DEFAULT KEY,
           END OF ty_tr_deep.

    " object_usage 분기용
    TYPES: BEGIN OF ty_usage_flat,
             pgmid       TYPE string,
             object      TYPE string,
             obj_type    TYPE string,
             caller      TYPE string,
             caller_type TYPE string,
             operation   TYPE string,
           END OF ty_usage_flat.
    TYPES: ty_usages_flat TYPE STANDARD TABLE OF ty_usage_flat WITH DEFAULT KEY.
    TYPES: BEGIN OF ty_payload_usage,
             trkorr TYPE string,
             usages TYPE ty_usages_flat,
           END OF ty_payload_usage.

    DATA: lt_e070  TYPE TABLE OF e070,
          lt_e071  TYPE TABLE OF e071,
          lt_e071k TYPE TABLE OF e071k,
          lt_e07t  TYPE TABLE OF e07t,
          lt_deep  TYPE STANDARD TABLE OF ty_tr_deep,
          ls_deep  TYPE ty_tr_deep.

    " =================================================================
    " 1. 파라미터 수신
    " =================================================================
    lv_user_id = server->request->get_form_field( 'user_id' ).
    TRANSLATE lv_user_id TO UPPER CASE.
    lv_action = server->request->get_form_field( 'action' ).

    " =================================================================
    " [분기 1] 종속성 맵 (Impact Analysis 엔진)
    " =================================================================
    IF lv_action = 'dependency'.
      lv_target_obj = server->request->get_form_field( 'target_obj' ).
      CONDENSE lv_target_obj. TRANSLATE lv_target_obj TO UPPER CASE.

      WRITE sy-datum TO lv_timestamp.
      ls_graph-snapshot_time = lv_timestamp && ' ' && sy-uzeit.

      IF lv_target_obj IS NOT INITIAL.
        APPEND VALUE #( id = lv_target_obj group = 1 name = lv_target_obj ) TO lt_nodes.

        " 1. 내 프로그램이 사용하는 객체 수집 (D010TAB)
        SELECT tabname FROM d010tab INTO TABLE @DATA(lt_raw_tabs)
          WHERE master = @lv_target_obj.

        IF lt_raw_tabs IS NOT INITIAL.
          " 필터: 시스템 메타데이터 및 단순 참조용 테이블 완전 배제
          SELECT tabname FROM dd02l INTO TABLE @DATA(lt_real_tabs)
            FOR ALL ENTRIES IN @lt_raw_tabs
            WHERE tabname = @lt_raw_tabs-tabname
              AND tabclass = 'TRANSP'
              AND tabname NOT LIKE 'DD%'
              AND tabname NOT LIKE 'E07%'
              AND tabname NOT LIKE 'ICON%'
              AND tabname NOT IN ('VARI', 'TVARVC', 'T100', 'SYST', 'T001').

          " 2. 살아남은 진짜 비즈니스 테이블을 공유하는 다른 Z프로그램 추적
          IF lt_real_tabs IS NOT INITIAL.
            SELECT master, tabname FROM d010tab INTO TABLE @DATA(lt_shared)
              FOR ALL ENTRIES IN @lt_real_tabs
              WHERE tabname = @lt_real_tabs-tabname
                AND master LIKE 'Z%'
                AND master <> @lv_target_obj.

            LOOP AT lt_shared INTO DATA(ls_shared).
              SELECT COUNT(*) FROM d010tab WHERE tabname = @ls_shared-tabname.
              IF sy-dbcnt > 30. CONTINUE. ENDIF.

              APPEND VALUE #( id = ls_shared-tabname group = 4 name = ls_shared-tabname ) TO lt_nodes.
              APPEND VALUE #( id = ls_shared-master group = 2 name = ls_shared-master ) TO lt_nodes.
              APPEND VALUE #( source = lv_target_obj target = ls_shared-tabname ) TO lt_links.
              APPEND VALUE #( source = ls_shared-master target = ls_shared-tabname ) TO lt_links.
            ENDLOOP.
          ENDIF.
        ENDIF.

        " 3. 실행 로직 (Function/Method) 연동
        SELECT include AS source, name AS target FROM wbcrossgt
          INTO CORRESPONDING FIELDS OF TABLE @lt_logic_links
          UP TO 200 ROWS
          WHERE include = @lv_target_obj
            AND otype IN ('PR', 'FU', 'ME', 'CL').

        LOOP AT lt_logic_links INTO DATA(ls_logic).
          APPEND VALUE #( id = ls_logic-target group = 3 name = ls_logic-target ) TO lt_nodes.
          APPEND VALUE #( source = ls_logic-source target = ls_logic-target ) TO lt_links.
        ENDLOOP.

        SORT lt_nodes BY id. DELETE ADJACENT DUPLICATES FROM lt_nodes COMPARING id.
        SORT lt_links BY source target. DELETE ADJACENT DUPLICATES FROM lt_links COMPARING source target.
      ENDIF.

      ls_graph-nodes = lt_nodes.
      ls_graph-links = lt_links.

      lv_json = /ui2/cl_json=>serialize( data = ls_graph compress = abap_true pretty_name = /ui2/cl_json=>pretty_mode-low_case ).
      server->response->set_cdata( lv_json ).
      server->response->set_header_field( name = 'Content-Type' value = 'application/json; charset=utf-8' ).
      server->response->set_status( code = 200 reason = 'OK' ).

    " =================================================================
    "  [분기 2] 시스템 전체 스냅샷 추출 (장고가 데이터를 당겨갈 때 사용)
    " =================================================================
    ELSEIF lv_action = 'snapshot'.
      TYPES: BEGIN OF ty_dependency,
               source TYPE string,
               target TYPE string,
               group  TYPE i,
             END OF ty_dependency.
      TYPES: BEGIN OF ty_payload,
               dependencies TYPE STANDARD TABLE OF ty_dependency WITH DEFAULT KEY,
             END OF ty_payload.

      DATA: ls_payload TYPE ty_payload,
            lt_deps    TYPE STANDARD TABLE OF ty_dependency.

      " 1. DB 테이블 종속성 추출 및 필터링
      SELECT master, tabname FROM d010tab INTO TABLE @DATA(lt_snap_tabs) WHERE master LIKE 'Z%'.
      IF sy-subrc = 0.
        DELETE lt_snap_tabs WHERE tabname CP 'DD*' OR tabname CP 'E07*' OR tabname CP 'ICON*'
                               OR tabname = 'VARI' OR tabname = 'TVARVC' OR tabname = 'T100'
                               OR tabname = 'SYST' OR tabname = 'T001' OR tabname = 'ALV_S_SORT'.
        IF lt_snap_tabs IS NOT INITIAL.
          SELECT tabname FROM dd02l INTO TABLE @DATA(lt_snap_dd02l)
            FOR ALL ENTRIES IN @lt_snap_tabs
            WHERE tabname = @lt_snap_tabs-tabname AND tabclass = 'TRANSP'.

          LOOP AT lt_snap_tabs INTO DATA(ls_snap_tab).
            READ TABLE lt_snap_dd02l TRANSPORTING NO FIELDS WITH KEY tabname = ls_snap_tab-tabname.
            IF sy-subrc = 0.
              APPEND VALUE #( source = ls_snap_tab-master target = ls_snap_tab-tabname group = 4 ) TO lt_deps.
            ENDIF.
          ENDLOOP.
        ENDIF.
      ENDIF.

      " 2. 로직 호출 종속성 추출
      SELECT include AS source, name AS target, otype FROM wbcrossgt INTO TABLE @DATA(lt_snap_cross)
        WHERE include LIKE 'Z%' AND otype IN ('PR', 'FU', 'ME', 'CL').

      LOOP AT lt_snap_cross INTO DATA(ls_snap_cross).
        DATA(lv_snap_grp) = 2.
        IF ls_snap_cross-otype = 'FU'. lv_snap_grp = 3. ENDIF.
        APPEND VALUE #( source = ls_snap_cross-source target = ls_snap_cross-target group = lv_snap_grp ) TO lt_deps.
      ENDLOOP.

      " 3. 중복 제거 및 조립
      SORT lt_deps BY source target.
      DELETE ADJACENT DUPLICATES FROM lt_deps COMPARING source target.

      ls_payload-dependencies = lt_deps.

      " 4. 장고로 JSON 응답
      lv_json = /ui2/cl_json=>serialize( data = ls_payload compress = abap_true pretty_name = /ui2/cl_json=>pretty_mode-low_case ).

      server->response->set_cdata( lv_json ).
      server->response->set_header_field( name = 'Content-Type' value = 'application/json; charset=utf-8' ).
      server->response->set_status( code = 200 reason = 'OK' ).

    " =================================================================
    " [분기 3] AI 코드 리뷰를 위한 원본 소스코드 조회
    " =================================================================
    ELSEIF lv_action = 'get_code'.
      lv_obj_name = server->request->get_form_field( 'obj_name' ).
      TRANSLATE lv_obj_name TO UPPER CASE.

      " 프로그램 소스코드를 배열 형태로 읽어오기
      READ REPORT lv_obj_name INTO lt_source.

      IF sy-subrc = 0.
        " 라인별 코드를 줄바꿈 기호(\n)를 기준으로 하나의 긴 텍스트로 합침
        CONCATENATE LINES OF lt_source INTO lv_source
                    SEPARATED BY cl_abap_char_utilities=>newline.

        " JSON 포맷 에러를 방지하기 위해 따옴표 및 특수문자 Escape 처리
        lv_source = escape( val = lv_source format = cl_abap_format=>e_json_string ).

        lv_json = |\{ "status": "success", "source_code": "{ lv_source }" \}|.
      ELSE.
        lv_json = |\{ "status": "error", "source_code": "SAP 서버에서 해당 프로그램({ lv_obj_name })의 코드를 읽을 수 없습니다." \}|.
      ENDIF.

      server->response->set_cdata( lv_json ).
      server->response->set_header_field( name = 'Content-Type' value = 'application/json; charset=utf-8' ).
      server->response->set_status( code = 200 reason = 'OK' ).

    " =================================================================
    " [분기 4] TR 오브젝트 사용처 (CALL/SUBMIT/MODIFY/UPDATE/INSERT/DELETE/APPEND/SELECT)
    " =================================================================
    ELSEIF lv_action = 'object_usage'.
      DATA: lv_trkorr_usage TYPE e070-trkorr,
            lt_trkorrs      TYPE TABLE OF e070-trkorr,
            lt_e071_usage   TYPE TABLE OF e071,
            lv_usage_json   TYPE string.
      DATA: lt_usages_flat TYPE ty_usages_flat,
            ls_usage_flat  TYPE ty_usage_flat,
            lt_src         TYPE TABLE OF string,
            lv_line        TYPE string,
            lv_obj         TYPE string,
            lv_obj_upper   TYPE string,
            lv_found       TYPE abap_bool,
            lt_masters     TYPE TABLE OF d010tab-master,
            lv_master      TYPE progname,
            lv_cnt         TYPE i.

      lv_trkorr_usage = server->request->get_form_field( 'trkorr' ).
      CONDENSE lv_trkorr_usage. TRANSLATE lv_trkorr_usage TO UPPER CASE.
      IF lv_trkorr_usage IS NOT INITIAL.
        APPEND lv_trkorr_usage TO lt_trkorrs.
        SELECT trkorr FROM e070 INTO TABLE @DATA(lt_sub_trs) WHERE strkorr = @lv_trkorr_usage.
        LOOP AT lt_sub_trs INTO DATA(ls_sub_tr). APPEND ls_sub_tr-trkorr TO lt_trkorrs. ENDLOOP.
        SORT lt_trkorrs. DELETE ADJACENT DUPLICATES FROM lt_trkorrs.

        SELECT * FROM e071 INTO TABLE @lt_e071_usage FOR ALL ENTRIES IN @lt_trkorrs WHERE trkorr = @lt_trkorrs-table_line.
        SORT lt_e071_usage BY object obj_name. DELETE ADJACENT DUPLICATES FROM lt_e071_usage COMPARING object obj_name.

        LOOP AT lt_e071_usage INTO DATA(ls_ou).
          CLEAR ls_usage_flat. ls_usage_flat-pgmid = ls_ou-pgmid. ls_usage_flat-object = ls_ou-obj_name. ls_usage_flat-obj_type = ls_ou-object.
          lv_obj = ls_ou-obj_name. lv_obj_upper = lv_obj. TRANSLATE lv_obj_upper TO UPPER CASE.

          CASE ls_ou-object.
            WHEN 'PROG' OR 'REPS'.
              SELECT include FROM wbcrossgt INTO TABLE @DATA(lt_callers_prog)
                WHERE name = @lv_obj AND otype IN ('PR','FU','ME','CL') AND include LIKE 'Z%'.
              LOOP AT lt_callers_prog INTO DATA(lv_caller). ls_usage_flat-caller = lv_caller. ls_usage_flat-caller_type = 'PROG'. ls_usage_flat-operation = 'CALL'. APPEND ls_usage_flat TO lt_usages_flat. ENDLOOP.
            WHEN 'TABL' OR 'DTEL'.
              lv_cnt = lines( lt_usages_flat ).
              SELECT master FROM d010tab INTO TABLE @lt_masters UP TO 30 ROWS WHERE tabname = @lv_obj AND master LIKE 'Z%'.
              LOOP AT lt_masters INTO lv_master.
                CLEAR lt_src. READ REPORT lv_master INTO lt_src.
                IF sy-subrc <> 0. CONTINUE. ENDIF.
                LOOP AT lt_src INTO lv_line.
                  TRANSLATE lv_line TO UPPER CASE.
                  SHIFT lv_line LEFT DELETING LEADING space.
                  IF strlen( lv_line ) > 0 AND lv_line(1) = '*'.
                    CONTINUE.
                  ENDIF.
                  lv_found = abap_false.
                  IF lv_line CS lv_obj_upper.
                    IF lv_line CS 'MODIFY' AND lv_line NS 'MODIFYING'. ls_usage_flat-operation = 'MODIFY'. lv_found = abap_true. ENDIF.
                    IF ( lv_line CS ' UPDATE ' OR lv_line CP 'UPDATE*' ) AND lv_found = abap_false. ls_usage_flat-operation = 'UPDATE'. lv_found = abap_true. ENDIF.
                    IF ( lv_line CS ' INSERT ' OR lv_line CP 'INSERT*' ) AND lv_found = abap_false. ls_usage_flat-operation = 'INSERT'. lv_found = abap_true. ENDIF.
                    IF ( lv_line CS ' DELETE ' OR lv_line CP 'DELETE*' ) AND lv_found = abap_false. ls_usage_flat-operation = 'DELETE'. lv_found = abap_true. ENDIF.
                    IF ( lv_line CS ' APPEND ' OR lv_line CP 'APPEND*' ) AND lv_found = abap_false. ls_usage_flat-operation = 'APPEND'. lv_found = abap_true. ENDIF.
                    " SELECT 단일문만 인정 (SELECT-OPTIONS, SELECTION-SCREEN 제외)
                    IF ( lv_line CS ' SELECT ' OR lv_line CP 'SELECT*' ) AND lv_line NS 'SELECT-OPTIONS' AND lv_line NS 'SELECTION-SCREEN' AND lv_found = abap_false.
                      ls_usage_flat-operation = 'SELECT'. lv_found = abap_true.
                    ENDIF.
                    IF lv_found = abap_true.
                      ls_usage_flat-caller = lv_master. ls_usage_flat-caller_type = 'PROG'. APPEND ls_usage_flat TO lt_usages_flat. EXIT.
                    ENDIF.
                  ENDIF.
                ENDLOOP.
              ENDLOOP.
              IF lines( lt_usages_flat ) = lv_cnt.
                SELECT master FROM d010tab INTO TABLE @lt_masters UP TO 20 ROWS WHERE tabname = @lv_obj AND master LIKE 'Z%'.
                LOOP AT lt_masters INTO lv_master.
                  ls_usage_flat-caller = lv_master. ls_usage_flat-caller_type = 'PROG'. ls_usage_flat-operation = 'TABLE_REF'. APPEND ls_usage_flat TO lt_usages_flat.
                ENDLOOP.
              ENDIF.
            WHEN 'CLAS'.
              SELECT include FROM wbcrossgt INTO TABLE @DATA(lt_clas_callers)
                WHERE name = @lv_obj AND otype = 'CL' AND include LIKE 'Z%'.
              LOOP AT lt_clas_callers INTO DATA(lv_cl). ls_usage_flat-caller = lv_cl. ls_usage_flat-caller_type = 'PROG'. ls_usage_flat-operation = 'CALL'. APPEND ls_usage_flat TO lt_usages_flat. ENDLOOP.
            WHEN OTHERS.
              " 기타 오브젝트는 사용처 생략
          ENDCASE.
        ENDLOOP.

        DATA(ls_payload_usage) = VALUE ty_payload_usage( trkorr = lv_trkorr_usage usages = lt_usages_flat ).
        lv_usage_json = /ui2/cl_json=>serialize( data = ls_payload_usage compress = abap_true pretty_name = /ui2/cl_json=>pretty_mode-low_case ).
      ELSE.
        lv_usage_json = |\{ "trkorr": "", "usages": [] \}|.
      ENDIF.
      server->response->set_cdata( lv_usage_json ).
      server->response->set_header_field( name = 'Content-Type' value = 'application/json; charset=utf-8' ).
      server->response->set_status( code = 200 reason = 'OK' ).

    " =================================================================
    " [분기 5] 메인 TR 목록 및 데이터 추출 로직
    " =================================================================
    ELSE.
      IF lv_user_id IS NOT INITIAL.
        SELECT * FROM e070 INTO TABLE @lt_e070 UP TO 200 ROWS
                 WHERE as4user = @lv_user_id
                 ORDER BY as4date DESCENDING, as4time DESCENDING.
      ELSE.
        SELECT * FROM e070 INTO TABLE @lt_e070 UP TO 10 ROWS
                 ORDER BY as4date DESCENDING, as4time DESCENDING.
      ENDIF.

      IF lt_e070 IS NOT INITIAL.
        SELECT trkorr, strkorr FROM e070 INTO TABLE @DATA(lt_sub_tasks)
          FOR ALL ENTRIES IN @lt_e070
          WHERE strkorr = @lt_e070-trkorr.

        LOOP AT lt_e070 INTO DATA(ls_temp).
          APPEND ls_temp-trkorr TO lt_all_trkorr.
        ENDLOOP.
        LOOP AT lt_sub_tasks INTO DATA(ls_sub_task).
          APPEND ls_sub_task-trkorr TO lt_all_trkorr.
        ENDLOOP.
        SORT lt_all_trkorr. DELETE ADJACENT DUPLICATES FROM lt_all_trkorr.

        IF lt_all_trkorr IS NOT INITIAL.
          SELECT * FROM e071 INTO TABLE @lt_e071 FOR ALL ENTRIES IN @lt_all_trkorr WHERE trkorr = @lt_all_trkorr-table_line.
          SELECT * FROM e071k INTO TABLE @lt_e071k FOR ALL ENTRIES IN @lt_all_trkorr WHERE trkorr = @lt_all_trkorr-table_line.
        ENDIF.
        SELECT * FROM e07t INTO TABLE @lt_e07t FOR ALL ENTRIES IN @lt_e070 WHERE trkorr = @lt_e070-trkorr.

        LOOP AT lt_e070 INTO DATA(ls_e070).
          CLEAR ls_deep. MOVE-CORRESPONDING ls_e070 TO ls_deep.
          READ TABLE lt_e07t INTO DATA(ls_e07t) WITH KEY trkorr = ls_e070-trkorr langu = sy-langu.
          IF sy-subrc <> 0.
            READ TABLE lt_e07t INTO ls_e07t WITH KEY trkorr = ls_e070-trkorr.
          ENDIF.
          IF sy-subrc = 0. ls_deep-as4text = ls_e07t-as4text. ENDIF.

          LOOP AT lt_e071 INTO DATA(ls_e071) WHERE trkorr = ls_e070-trkorr.
            APPEND ls_e071 TO ls_deep-objects.
          ENDLOOP.
          LOOP AT lt_e071k INTO DATA(ls_e071k) WHERE trkorr = ls_e070-trkorr.
            APPEND ls_e071k TO ls_deep-keys.
          ENDLOOP.

          LOOP AT lt_sub_tasks INTO DATA(ls_st) WHERE strkorr = ls_e070-trkorr.
            LOOP AT lt_e071 INTO DATA(ls_sub_e071) WHERE trkorr = ls_st-trkorr.
              APPEND ls_sub_e071 TO ls_deep-objects.
            ENDLOOP.
            LOOP AT lt_e071k INTO DATA(ls_sub_e071k) WHERE trkorr = ls_st-trkorr.
              APPEND ls_sub_e071k TO ls_deep-keys.
            ENDLOOP.
          ENDLOOP.
          APPEND ls_deep TO lt_deep.
        ENDLOOP.
      ENDIF.

      lv_json = /ui2/cl_json=>serialize( data = lt_deep ).
      server->response->set_cdata( lv_json ).
      server->response->set_header_field( name = 'Content-Type' value = 'application/json; charset=utf-8' ).
      server->response->set_status( code = 200 reason = 'OK' ).
    ENDIF.

ENDMETHOD.