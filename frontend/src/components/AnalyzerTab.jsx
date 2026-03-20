import React from 'react';
import { getTrObjectsTree } from '../utils/trUtils';
import DeployReportModal from './DeployReportModal';
import CodeReviewModal from './CodeReviewModal';

function checkIfReviewNeeded(trkorr, trDesc, rawTrData) {
  if (trDesc && trDesc.includes('[IMG]')) return false;
  const tree = getTrObjectsTree(trkorr, rawTrData);
  if (Object.keys(tree).length === 0) return false;
  return ['PROG', 'CLAS', 'FUGR'].some((type) => tree[type] && tree[type].size > 0);
}

export default function AnalyzerTab({
  userId,
  setUserId,
  trList,
  rawTrData,
  expandedTr,
  setExpandedTr,
  selectedTrs,
  loadingList,
  loadingAnalysis,
  analyzerResponse,
  isReportModalOpen,
  setIsReportModalOpen,
  elapsedTime,
  analyzeProgress,
  analyzeCompletedSteps,
  reviewedTrs,
  deployApprovedTrs,
  savedAiReviews,
  isReviewPanelOpen,
  closeReviewPanel,
  currentReviewData,
  isEditingTicketSpec,
  setIsEditingTicketSpec,
  editTicketId,
  setEditTicketId,
  editDesc,
  setEditDesc,
  savingTicketMapping,
  writingToSap,
  setSelectedTrs,
  handleSearch,
  handleAnalyze,
  handleApproveDeploy,
  handleDownload,
  openReviewPanel,
  startEditTicketSpec,
  saveTicketMapping,
  executeCodeReview,
  writeRefactoredToSap,
  confirmReview,
  reverseReview,
  openCachedReviewByTr,
  extractRefactoredCode,
  setLoadingAnalysis,
  reportModalTargetTrs,
  openDeployReportForTr,
}) {
  const toggleTrExpand = (trkorr) => setExpandedTr((prev) => (prev === trkorr ? null : trkorr));
  const handleCheckboxChange = (trkorr) => {
    setSelectedTrs((prev) => (prev.includes(trkorr) ? prev.filter((id) => id !== trkorr) : [...prev, trkorr]));
  };

  const blockingTrs = selectedTrs.filter((trkorr) => {
    const tr = rawTrData.find((t) => (t.TRKORR || t.trkorr) === trkorr);
    if (!tr) return false;
    const isRequired = checkIfReviewNeeded(trkorr, tr.AS4TEXT || tr.as4text, rawTrData);
    const isReviewed = reviewedTrs.includes(trkorr);
    return isRequired && !isReviewed;
  });
  const isDeployReady = selectedTrs.length > 0 && blockingTrs.length === 0;

  const getReviewBtnForObj = (trkorr, objName, objType) => {
    const isCached = !!savedAiReviews[`${trkorr}_${objName}`];
    return (
      <button
        onClick={(e) => {
          e.stopPropagation();
          openReviewPanel(trkorr, objName, objType);
        }}
        style={{
          marginLeft: '10px',
          background: isCached ? '#238636' : '#3a284a',
          border: 'none',
          color: isCached ? '#fff' : '#cda8ff',
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '11px',
          cursor: 'pointer',
          fontWeight: 'bold',
        }}
      >
        {isCached ? '✅ 리뷰 결과 보기' : '🔍 AI 코드리뷰'}
      </button>
    );
  };

  return (
    <div className="analyzer-container" style={{ position: 'relative' }}>
      <div className="analyzer-search-wrapper">
        <input
          type="text"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="User ID 입력 (예: 11355)"
        />
        <button onClick={handleSearch} disabled={loadingList}>
          {loadingList ? '검색 중...' : 'TR 목록 조회'}
        </button>
      </div>

      {trList.length > 0 && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
            <h3 style={{ color: '#fff', margin: 0 }}>조회된 메인 TR 목록 ({trList.length}건)</h3>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                onClick={handleAnalyze}
                disabled={loadingAnalysis || selectedTrs.length === 0 || !isDeployReady}
                style={{
                  backgroundColor: selectedTrs.length > 0 && isDeployReady ? '#a8cdff' : '#444',
                  color: selectedTrs.length > 0 && isDeployReady ? '#000' : '#888',
                  padding: '8px 15px',
                  borderRadius: '6px',
                  fontWeight: 'bold',
                  border: 'none',
                  cursor: selectedTrs.length > 0 && isDeployReady ? 'pointer' : 'not-allowed',
                  fontSize: '13px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                {loadingAnalysis ? (
                  <>
                    <div className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px', borderColor: '#000', borderTopColor: 'transparent' }}></div>
                    실시간 모듈별 심의 진행 중...
                  </>
                ) : selectedTrs.length === 0 ? (
                  '배포 심의 요청 (TR 선택 필요)'
                ) : !isDeployReady ? (
                  `⚠️ 리뷰 미완료 해제 필요 (막힌 TR: ${blockingTrs.length}건)`
                ) : (
                  `🚀 ${selectedTrs.length}건 배포 심의 요청`
                )}
              </button>
              <button
                onClick={handleSearch}
                disabled={loadingList}
                style={{ backgroundColor: '#2b2b2b', color: '#fff', border: '1px solid #444', padding: '8px 15px', borderRadius: '6px', cursor: 'pointer', fontSize: '13px' }}
              >
                {loadingList ? '새로고침 중...' : '목록 새로고침'}
              </button>
            </div>
          </div>

          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '50px', whiteSpace: 'nowrap', textAlign: 'center' }}>선택</th>
                <th style={{ width: '120px', whiteSpace: 'nowrap', textAlign: 'center' }}>TR 번호</th>
                <th>내역</th>
                <th style={{ width: '60px', whiteSpace: 'nowrap', textAlign: 'center' }}>유형</th>
                <th style={{ width: '90px', whiteSpace: 'nowrap', textAlign: 'center' }}>AI 리뷰</th>
                <th style={{ width: '120px', whiteSpace: 'nowrap', textAlign: 'center' }}>배포 심의</th>
              </tr>
            </thead>
            <tbody>
              {trList.map((tr) => {
                const trkorr = tr.TRKORR || tr.trkorr;
                const trDesc = tr.AS4TEXT || tr.as4text || '';
                const isExpanded = expandedTr === trkorr;
                const treeData = isExpanded ? getTrObjectsTree(trkorr, rawTrData) : {};
                const isReviewRequired = checkIfReviewNeeded(trkorr, trDesc, rawTrData);
                const isReviewed = reviewedTrs.includes(trkorr);
                const isApproved = deployApprovedTrs.includes(trkorr);

                return (
                  <React.Fragment key={trkorr}>
                    <tr
                      onClick={() => toggleTrExpand(trkorr)}
                      style={{ cursor: 'pointer', backgroundColor: isExpanded ? '#2b2b2b' : 'transparent', transition: 'background-color 0.2s' }}
                    >
                      <td style={{ textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                        <input type="checkbox" checked={selectedTrs.includes(trkorr)} onChange={() => handleCheckboxChange(trkorr)} />
                      </td>
                      <td style={{ textAlign: 'center', fontWeight: 'bold', color: 'var(--accent-color)' }}>
                        {isExpanded ? '▼ ' : '▶ '} {trkorr}
                      </td>
                      <td>{trDesc || '내역 없음'}</td>
                      <td style={{ textAlign: 'center' }}>{tr.TRFUNCTION || tr.trfunction}</td>
                      <td style={{ textAlign: 'center' }} onClick={(e) => { if (isReviewed) { e.stopPropagation(); setExpandedTr(trkorr); } }}>
                        {!isReviewRequired ? (
                          <span style={{ color: '#64b5f6', fontSize: '12px' }}>🔵 불필요</span>
                        ) : isReviewed ? (
                          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                            <span style={{ color: '#4caf50', fontWeight: 'bold', fontSize: '12px' }}>✅ 완료</span>
                            <span
                              onClick={(e) => { e.stopPropagation(); openCachedReviewByTr(trkorr); }}
                              style={{ fontSize: '11px', color: '#a8cdff', textDecoration: 'underline', cursor: 'pointer', backgroundColor: '#2b2b2b', padding: '2px 6px', borderRadius: '4px' }}
                            >
                              🔍 레포트
                            </span>
                          </div>
                        ) : (
                          <span style={{ color: '#888', fontSize: '12px' }}>⏳ 미완료</span>
                        )}
                      </td>
                      <td style={{ textAlign: 'center' }} onClick={(e) => { if (isApproved) e.stopPropagation(); }}>
                        {isApproved ? (
                          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                            <span style={{ backgroundColor: '#238636', color: '#fff', padding: '2px 6px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold' }}>🚀 승인됨</span>
                            <span
                              onClick={(e) => { e.stopPropagation(); openDeployReportForTr(trkorr); }}
                              style={{ fontSize: '11px', color: '#a8cdff', textDecoration: 'underline', cursor: 'pointer', backgroundColor: '#2b2b2b', padding: '2px 6px', borderRadius: '4px' }}
                            >
                              📄 레포트
                            </span>
                          </div>
                        ) : (
                          <span style={{ color: '#666', fontSize: '12px' }}>-</span>
                        )}
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr style={{ backgroundColor: '#1a1a1a' }}>
                        <td colSpan="6" style={{ padding: '15px 30px', borderBottom: '1px solid var(--border-color)' }}>
                          <div style={{ fontSize: '13px', color: '#ccc' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', color: '#888' }}>
                              <div>
                                <span style={{ marginRight: '6px' }}>📁</span>
                                <strong>포함된 오브젝트</strong>
                              </div>
                              {isReviewed && (
                                <button
                                  onClick={(e) => { e.stopPropagation(); reverseReview(trkorr); }}
                                  style={{ background: 'transparent', border: '1px solid #ff6b6b', color: '#ff6b6b', borderRadius: '4px', padding: '2px 8px', fontSize: '11px', cursor: 'pointer' }}
                                >
                                  ↩️ 리뷰/승인 상태 초기화
                                </button>
                              )}
                            </div>
                            {Object.keys(treeData).length > 0 ? (
                              <div style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                {Object.entries(treeData).map(([objType, objSet]) => (
                                  <div key={objType}>
                                    <div style={{ color: '#a8cdff', fontWeight: 'bold', marginBottom: '6px' }}>
                                      📁 {objType} ({objSet.size}개)
                                    </div>
                                    <div style={{ paddingLeft: '24px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                      {Array.from(objSet).map((objName) => (
                                        <div
                                          key={objName}
                                          style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            backgroundColor: '#2b2b2b',
                                            padding: '4px 10px',
                                            borderRadius: '4px',
                                            border: '1px solid #444',
                                            fontSize: '12px',
                                          }}
                                        >
                                          📄 {objName}
                                          {(objType === 'PROG' || objType === 'CLAS' || objType === 'FUGR') && isReviewRequired && getReviewBtnForObj(trkorr, objName, objType)}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div style={{ paddingLeft: '20px', color: '#666' }}>포함된 오브젝트가 없습니다.</div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <DeployReportModal
        isOpen={isReportModalOpen}
        onClose={() => { setIsReportModalOpen(false); setLoadingAnalysis(false); }}
        loadingAnalysis={loadingAnalysis}
        elapsedTime={elapsedTime}
        analyzeCompletedSteps={analyzeCompletedSteps}
        analyzeProgress={analyzeProgress}
        analyzerResponse={analyzerResponse}
        displayTrkorrs={reportModalTargetTrs.length ? reportModalTargetTrs : selectedTrs}
        onDownload={handleDownload}
        onApproveDeploy={handleApproveDeploy}
      />

      <CodeReviewModal
        isOpen={isReviewPanelOpen}
        currentReviewData={currentReviewData}
        onClose={closeReviewPanel}
        isEditingTicketSpec={isEditingTicketSpec}
        editTicketId={editTicketId}
        setEditTicketId={setEditTicketId}
        editDesc={editDesc}
        setEditDesc={setEditDesc}
        savingTicketMapping={savingTicketMapping}
        writingToSap={writingToSap}
        onStartEditTicketSpec={startEditTicketSpec}
        onSaveTicketMapping={saveTicketMapping}
        onCancelEditTicketSpec={() => setIsEditingTicketSpec(false)}
        onExecuteCodeReview={executeCodeReview}
        onWriteRefactoredToSap={writeRefactoredToSap}
        onConfirmReview={confirmReview}
        extractRefactoredCode={extractRefactoredCode}
      />
    </div>
  );
}
