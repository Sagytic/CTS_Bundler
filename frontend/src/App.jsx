import React, { useState, useRef, useEffect } from 'react';
import ReactFlow, { useNodesState, useEdgesState } from 'reactflow';
import 'reactflow/dist/style.css';
import './App.css';
import { api } from './api/client';
import { streamCodeReview } from './api/codeReviewStream';
import { streamAgentChat } from './api/agentStream';
import { streamDeployAnalysis } from './api/analyzeStream';
import { usePersistedJsonState } from './hooks/usePersistedJsonState';
import { filterMainTransports } from './utils/trUtils';
import { extractRefactoredCode } from './utils/markdownUtils';
import { deployBatchKey, findLatestDeployReportForTr } from './utils/deployReportStorage';
import Landing from './components/Landing';
import Sidebar from './components/Sidebar';
import AgentTab from './components/AgentTab';
import AnalyzerTab from './components/AnalyzerTab';
import DependencyTab from './components/DependencyTab';
import UsageDashboardTab from './components/UsageDashboardTab';
import SettingsModal from './components/SettingsModal';

function App() {
  const [loggedInUser, setLoggedInUser] = useState(null);
  const [loginId, setLoginId] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [agentStreamPreview, setAgentStreamPreview] = useState(null);
  const chatEndRef = useRef(null);
  const [userId, setUserId] = useState('');

  const [trList, setTrList] = useState([]);
  const [rawTrData, setRawTrData] = useState([]);
  const [expandedTr, setExpandedTr] = useState(null);
  const [selectedTrs, setSelectedTrs] = useState([]);

  const [loadingList, setLoadingList] = useState(false);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [analyzerResponse, setAnalyzerResponse] = useState('');
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [analyzeProgress, setAnalyzeProgress] = useState({ step: '', label: '' });
  const [analyzeCompletedSteps, setAnalyzeCompletedSteps] = useState([]);

  const [reviewedTrs, setReviewedTrs] = usePersistedJsonState('reviewedTrs', []);
  const [savedAiReviews, setSavedAiReviews] = usePersistedJsonState('savedAiReviews', {});
  const [deployApprovedTrs, setDeployApprovedTrs] = usePersistedJsonState('deployApprovedTrs', []);
  /** batchKey → { markdown, updatedAt, trkorrs } — 심의 레포트 TR 묶음별 영구 저장 */
  const [deployCommitteeReports, setDeployCommitteeReports] = usePersistedJsonState('deployCommitteeReports', {});
  /** 모달 하단·다운로드에 표시할 TR 목록 (실행 시점 또는 저장된 배치) */
  const [reportModalTargetTrs, setReportModalTargetTrs] = useState([]);

  const [isReviewPanelOpen, setIsReviewPanelOpen] = useState(false);
  const [currentReviewData, setCurrentReviewData] = useState(null);
  const [isEditingTicketSpec, setIsEditingTicketSpec] = useState(false);
  const [editTicketId, setEditTicketId] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [savingTicketMapping, setSavingTicketMapping] = useState(false);
  const [writingToSap, setWritingToSap] = useState(false);

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [settingUserId, setSettingUserId] = useState(localStorage.getItem('sapUserId') || '');
  const [settingLlmModel, setSettingLlmModel] = useState(localStorage.getItem('llmModel') || 'gpt-4o');

  const [targetObj, setTargetObj] = useState('');
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [expandingNodeId, setExpandingNodeId] = useState(null);
  const [isSnapshotUpdating, setIsSnapshotUpdating] = useState(false);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [, setSelectedNodeId] = useState(null);
  const nodesRef = useRef(nodes);
  const edgesRef = useRef(edges);
  nodesRef.current = nodes;
  edgesRef.current = edges;

  const codeReviewAbortRef = useRef(null);

  const closeReviewPanel = () => {
    codeReviewAbortRef.current?.abort();
    setIsReviewPanelOpen(false);
  };

  useEffect(() => {
    if (activeTab === 'chat' && chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatHistory, activeTab, isChatLoading, agentStreamPreview]);

  const handleSaveSettings = () => {
    localStorage.setItem('sapUserId', settingUserId);
    localStorage.setItem('llmModel', settingLlmModel);
    setUserId(settingUserId);
    setIsSettingsOpen(false);
    alert('설정이 저장되었습니다.');
  };

  const handleSnapshotUpdate = async () => {
    setIsSnapshotUpdating(true);
    try {
      const res = await api.get('/api/snapshot/update/');
      if (res.status === 200) {
        alert(`✅ 스냅샷 업데이트 성공!\n총 ${res.data.total_records.toLocaleString()}건 갱신 완료.`);
      }
    } catch {
      alert('업데이트 실패');
    } finally {
      setIsSnapshotUpdating(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!loginId.trim()) return;
    setIsLoggingIn(true);
    try {
      await api.post('/api/login/', { user_id: loginId });
      const res = await api.get('/api/transports/');
      const allTrs = res.data.transports || [];
      const mainTrs = filterMainTransports(allTrs);
      setRawTrData(allTrs);
      if (mainTrs.length === 0) {
        alert('생성한 메인 TR이 없습니다.');
        setIsLoggingIn(false);
        return;
      }
      setTrList(mainTrs);
      setLoggedInUser(loginId);
      setUserId(loginId);
      setSettingUserId(loginId);
      localStorage.setItem('sapUserId', loginId);
    } catch {
      alert('서버 연결 실패');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleSearch = async () => {
    if (!userId.trim()) return;
    setLoadingList(true);
    setTrList([]);
    setSelectedTrs([]);
    setAnalyzerResponse('');
    setExpandedTr(null);
    try {
      const res = await api.get('/api/transports/');
      const allTrs = res.data.transports || [];
      setRawTrData(allTrs);
      setTrList(filterMainTransports(allTrs));
    } catch {
      alert('TR 목록 가져오기 실패.');
    } finally {
      setLoadingList(false);
    }
  };

  const handleChatSubmit = async (textOverride = null) => {
    const textToSend = textOverride || chatInput;
    if (!textToSend.trim()) return;
    if (!textOverride) setChatInput('');
    setChatHistory((prev) => [...prev, { role: 'user', content: textToSend }]);
    setIsChatLoading(true);
    setAgentStreamPreview(null);
    try {
      const result = await streamAgentChat(
        {
          message: textToSend,
          include_steps: true,
        },
        {
          // 중간 토큰에 TR 목록·도구 원문이 먼저 보이는 문제 방지: 완료 후 한 번에 표시(스피너만 유지)
          onDelta: () => {},
        },
      );
      let content = result.reply || '응답 없음';
      if (result.error) {
        content = `${content}\n\n_(실행 오류: ${result.error})_`;
      }
      setChatHistory((prev) => [
        ...prev,
        {
          role: 'ai',
          content,
          steps: result.steps || [],
          react_used_tools: result.react_used_tools ?? 0,
        },
      ]);
    } catch (error) {
      const msg =
        typeof error?.message === 'string'
          ? error.message
          : '서버 연결에 실패했습니다.';
      setChatHistory((prev) => [
        ...prev,
        {
          role: 'ai',
          content: msg.slice(0, 2000),
          steps: [],
          react_used_tools: 0,
        },
      ]);
    } finally {
      setAgentStreamPreview(null);
      setIsChatLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleChatSubmit();
    }
  };
  const handleSuggestionClick = (question) => handleChatSubmit(question);

  const handleGoHome = () => {
    setActiveTab('chat');
    setChatHistory([]);
  };

  const handleAnalyze = async () => {
    if (selectedTrs.length === 0) return;
    const trsSnapshot = [...selectedTrs];
    const batchKey = deployBatchKey(trsSnapshot);
    setReportModalTargetTrs(trsSnapshot);
    setLoadingAnalysis(true);
    setAnalyzerResponse('');
    setElapsedTime(0);
    setAnalyzeProgress({ step: '', label: '' });
    setAnalyzeCompletedSteps([]);
    setIsReportModalOpen(true);
    const timerInterval = setInterval(() => setElapsedTime((prev) => prev + 1), 1000);
    let replyToStore = null;
    try {
      replyToStore = await streamDeployAnalysis(
        { message: '선택된 TR 분석', selected_trs: trsSnapshot },
        {
          setAnalyzeProgress,
          setAnalyzeCompletedSteps,
          setAnalyzerResponse,
        },
      );
    } catch {
      const errMsg = '분석 요청 중 오류가 발생했습니다.';
      setAnalyzerResponse(errMsg);
      replyToStore = errMsg;
    } finally {
      clearInterval(timerInterval);
      setLoadingAnalysis(false);
    }
    if (replyToStore && batchKey) {
      const trkorrsSorted = [...new Set(trsSnapshot.map(String))].sort();
      setDeployCommitteeReports((prev) => ({
        ...prev,
        [batchKey]: {
          markdown: replyToStore,
          updatedAt: Date.now(),
          trkorrs: trkorrsSorted,
        },
      }));
    }
  };

  /** 승인된 행의 📄 레포트: 해당 TR이 포함된 가장 최근 심의 배치 레포트 표시 */
  const openDeployReportForTr = (trkorr) => {
    const entry = findLatestDeployReportForTr(trkorr, deployCommitteeReports);
    if (!entry?.markdown) {
      alert(
        '해당 TR을 포함한 심의 레포트가 저장되어 있지 않습니다.\n' +
          '해당 TR을 체크한 뒤 "배포 심의 요청"을 실행하면 레포트가 저장됩니다.',
      );
      return;
    }
    setAnalyzerResponse(entry.markdown);
    setReportModalTargetTrs(entry.trkorrs?.length ? [...entry.trkorrs] : [String(trkorr)]);
    setLoadingAnalysis(false);
    setIsReportModalOpen(true);
  };

  const handleApproveDeploy = () => {
    /** 모달에 보이는 레포트의 TR 묶음 기준 승인 (재조회 시 체크박스와 불일치 방지) */
    const trs = reportModalTargetTrs.length > 0 ? reportModalTargetTrs : selectedTrs;
    setDeployApprovedTrs((prev) => [...new Set([...prev, ...trs])]);
    setIsReportModalOpen(false);
  };

  const handleDownload = () => {
    if (!analyzerResponse) return;
    const blob = new Blob([analyzerResponse], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const today = new Date();
    const dateStr = `${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, '0')}${String(today.getDate()).padStart(2, '0')}`;
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `CTS_심의결과_${userId}_${dateStr}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const openReviewPanel = async (trkorr, objName, objType) => {
    setIsEditingTicketSpec(false);
    const cacheKey = `${trkorr}_${objName}`;
    if (savedAiReviews[cacheKey]) {
      const c = savedAiReviews[cacheKey];
      setCurrentReviewData({
        trkorr,
        objName,
        objType,
        ticket: c.ticket,
        desc: c.desc,
        originalCode: c.originalCode,
        aiResult: c.aiResult,
        writtenToSap: c.writtenToSap,
        appliedSource: c.appliedSource,
        isLoading: false,
        isCodeLoading: false,
      });
      setIsReviewPanelOpen(true);
      return;
    }
    setCurrentReviewData({
      trkorr,
      objName,
      objType,
      ticket: '불러오는 중...',
      desc: '대기 중...',
      originalCode: '',
      aiResult: '',
      isLoading: false,
      isCodeLoading: true,
    });
    setIsReviewPanelOpen(true);
    try {
      const res = await api.get('/api/ticket-info/', { params: { trkorr, objName } });
      setCurrentReviewData((prev) => ({
        ...prev,
        ticket: res.data.ticket_id,
        desc: res.data.description,
        originalCode: res.data.abap_code,
        isCodeLoading: false,
      }));
    } catch {
      setCurrentReviewData((prev) => ({
        ...prev,
        ticket: '통신 오류',
        desc: '데이터를 불러올 수 없습니다.',
        originalCode: '코드 로드 실패',
        isCodeLoading: false,
      }));
    }
  };

  const startEditTicketSpec = () => {
    const t = currentReviewData?.ticket ?? '';
    const d = currentReviewData?.desc ?? '';
    setEditTicketId(t === '미매핑 (수동입력 필요)' || t === '불러오는 중...' ? '' : t);
    setEditDesc(d.includes('매핑된 현업 요구사항 티켓이 DB에 없습니다') || d === '대기 중...' ? '' : d);
    setIsEditingTicketSpec(true);
  };

  const saveTicketMapping = async () => {
    if (!currentReviewData?.trkorr) return;
    setSavingTicketMapping(true);
    try {
      const res = await api.post('/api/ticket-mapping/', {
        trkorr: currentReviewData.trkorr,
        ticket_id: editTicketId.trim() || '미매핑',
        description: editDesc.trim(),
      });
      setCurrentReviewData((prev) => ({ ...prev, ticket: res.data.ticket_id, desc: res.data.description }));
      setIsEditingTicketSpec(false);
    } catch (err) {
      console.error(err);
      alert('저장 실패: ' + (err.response?.data?.error || err.message));
    } finally {
      setSavingTicketMapping(false);
    }
  };

  const executeCodeReview = async () => {
    if (!currentReviewData) return;
    codeReviewAbortRef.current?.abort();
    const ac = new AbortController();
    codeReviewAbortRef.current = ac;

    const payload = {
      objName: currentReviewData.objName,
      trkorr: currentReviewData.trkorr,
      abapCode: currentReviewData.originalCode,
      requirementSpec: currentReviewData.desc || '',
    };

    setCurrentReviewData((prev) => ({
      ...prev,
      isLoading: true,
      aiResult: '',
    }));

    try {
      await streamCodeReview(payload, {
        signal: ac.signal,
        onDelta: (full) => {
          setCurrentReviewData((prev) => (prev ? { ...prev, aiResult: full } : prev));
        },
      });
      setCurrentReviewData((prev) => (prev ? { ...prev, isLoading: false } : prev));
    } catch (err) {
      if (err?.name === 'AbortError') {
        setCurrentReviewData((prev) => (prev ? { ...prev, isLoading: false } : prev));
        return;
      }
      const msg = err?.message || '서버 통신 실패';
      setCurrentReviewData((prev) =>
        prev
          ? {
              ...prev,
              isLoading: false,
              aiResult: prev.aiResult ? `${prev.aiResult}\n\n[오류] ${msg}` : `[오류] ${msg}`,
            }
          : prev,
      );
    }
  };

  const writeRefactoredToSap = async () => {
    const code = extractRefactoredCode(currentReviewData?.aiResult);
    if (!code) {
      alert('리팩토링 코드를 찾을 수 없습니다. AI 리뷰 결과에 ```abap ... ``` 블록이 있는지 확인하세요.');
      return;
    }
    if (!currentReviewData?.trkorr || !currentReviewData?.objName) return;
    setWritingToSap(true);
    try {
      const res = await api.post('/api/adt-write/', {
        objName: currentReviewData.objName,
        objType: currentReviewData.objType || 'PROG',
        newSource: code,
        trkorr: currentReviewData.trkorr,
      });
      if (res.data?.ok) {
        alert(res.data.message || 'SAP에 저장되었습니다.');
        const cacheKey = `${currentReviewData.trkorr}_${currentReviewData.objName}`;
        setCurrentReviewData((prev) => ({ ...prev, writtenToSap: true, appliedSource: code }));
        setSavedAiReviews((prev) => ({
          ...prev,
          [cacheKey]: {
            ...(prev[cacheKey] || {}),
            ticket: currentReviewData.ticket,
            desc: currentReviewData.desc,
            originalCode: currentReviewData.originalCode,
            aiResult: currentReviewData.aiResult,
            writtenToSap: true,
            appliedSource: code,
          },
        }));
      } else {
        alert(res.data?.error || '저장 실패');
      }
    } catch (err) {
      alert('SAP 쓰기 실패: ' + (err.response?.data?.error || err.message));
    } finally {
      setWritingToSap(false);
    }
  };

  const confirmReview = () => {
    if (!reviewedTrs.includes(currentReviewData.trkorr)) {
      setReviewedTrs((prev) => [...prev, currentReviewData.trkorr]);
    }
    const cacheKey = `${currentReviewData.trkorr}_${currentReviewData.objName}`;
    setSavedAiReviews((prev) => ({
      ...prev,
      [cacheKey]: {
        ticket: currentReviewData.ticket,
        desc: currentReviewData.desc,
        originalCode: currentReviewData.originalCode,
        aiResult: currentReviewData.aiResult,
        writtenToSap: currentReviewData.writtenToSap,
        appliedSource: currentReviewData.appliedSource,
      },
    }));
    closeReviewPanel();
  };

  const reverseReview = (trkorr) => {
    setReviewedTrs((prev) => prev.filter((id) => id !== trkorr));
    setDeployApprovedTrs((prev) => prev.filter((id) => id !== trkorr));
    setSavedAiReviews((prev) => {
      const newCache = { ...prev };
      Object.keys(newCache).forEach((key) => {
        if (key.startsWith(`${trkorr}_`)) delete newCache[key];
      });
      return newCache;
    });
  };

  const openCachedReviewByTr = (trkorr) => {
    const cacheKeys = Object.keys(savedAiReviews);
    const targetKey = cacheKeys.find((key) => key.startsWith(`${trkorr}_`));
    if (targetKey) {
      const objName = targetKey.split('_').slice(1).join('_');
      openReviewPanel(trkorr, objName, 'PROG');
    } else {
      alert('저장된 리뷰 상세 데이터를 찾을 수 없습니다.');
    }
  };

  if (!loggedInUser) {
    return (
      <Landing loginId={loginId} setLoginId={setLoginId} isLoggingIn={isLoggingIn} handleLogin={handleLogin} />
    );
  }

  return (
    <div className="app-layout">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isSidebarOpen={isSidebarOpen}
        setIsSidebarOpen={setIsSidebarOpen}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      <div className="main-wrapper">
        <div className="top-nav">
          <div className="logo-container" onClick={handleGoHome}>
            <img
              src="/logo.png"
              alt="CTS Bundler Logo"
              className="logo-img"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
          </div>
        </div>

        {activeTab === 'chat' && (
          <AgentTab
            history={chatHistory}
            input={chatInput}
            setInput={setChatInput}
            isLoading={isChatLoading}
            streamPreview={agentStreamPreview}
            chatEndRef={chatEndRef}
            trListLength={trList.length}
            setActiveTab={setActiveTab}
            handleSubmit={handleChatSubmit}
            handleKeyDown={handleKeyDown}
            handleSuggestionClick={handleSuggestionClick}
          />
        )}

        {activeTab === 'analyzer' && (
          <AnalyzerTab
            userId={userId}
            setUserId={setUserId}
            trList={trList}
            rawTrData={rawTrData}
            expandedTr={expandedTr}
            setExpandedTr={setExpandedTr}
            selectedTrs={selectedTrs}
            setSelectedTrs={setSelectedTrs}
            loadingList={loadingList}
            loadingAnalysis={loadingAnalysis}
            analyzerResponse={analyzerResponse}
            isReportModalOpen={isReportModalOpen}
            setIsReportModalOpen={setIsReportModalOpen}
            elapsedTime={elapsedTime}
            analyzeProgress={analyzeProgress}
            analyzeCompletedSteps={analyzeCompletedSteps}
            reviewedTrs={reviewedTrs}
            deployApprovedTrs={deployApprovedTrs}
            savedAiReviews={savedAiReviews}
            isReviewPanelOpen={isReviewPanelOpen}
            closeReviewPanel={closeReviewPanel}
            currentReviewData={currentReviewData}
            setCurrentReviewData={setCurrentReviewData}
            isEditingTicketSpec={isEditingTicketSpec}
            setIsEditingTicketSpec={setIsEditingTicketSpec}
            editTicketId={editTicketId}
            setEditTicketId={setEditTicketId}
            editDesc={editDesc}
            setEditDesc={setEditDesc}
            savingTicketMapping={savingTicketMapping}
            writingToSap={writingToSap}
            handleSearch={handleSearch}
            handleAnalyze={handleAnalyze}
            handleApproveDeploy={handleApproveDeploy}
            handleDownload={handleDownload}
            openReviewPanel={openReviewPanel}
            startEditTicketSpec={startEditTicketSpec}
            saveTicketMapping={saveTicketMapping}
            executeCodeReview={executeCodeReview}
            writeRefactoredToSap={writeRefactoredToSap}
            confirmReview={confirmReview}
            reverseReview={reverseReview}
            openCachedReviewByTr={openCachedReviewByTr}
            extractRefactoredCode={extractRefactoredCode}
            setLoadingAnalysis={setLoadingAnalysis}
            reportModalTargetTrs={reportModalTargetTrs}
            openDeployReportForTr={openDeployReportForTr}
          />
        )}

        {activeTab === 'usage' && <UsageDashboardTab />}

        {activeTab === 'dependency' && (
          <DependencyTab
            targetObj={targetObj}
            setTargetObj={setTargetObj}
            loadingGraph={loadingGraph}
            setLoadingGraph={setLoadingGraph}
            expandingNodeId={expandingNodeId}
            setExpandingNodeId={setExpandingNodeId}
            setSelectedNodeId={setSelectedNodeId}
            nodes={nodes}
            setNodes={setNodes}
            onNodesChange={onNodesChange}
            edges={edges}
            setEdges={setEdges}
            onEdgesChange={onEdgesChange}
            nodesRef={nodesRef}
            edgesRef={edgesRef}
            onSnapshotUpdate={handleSnapshotUpdate}
            isSnapshotUpdating={isSnapshotUpdating}
          />
        )}
      </div>

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        settingUserId={settingUserId}
        setSettingUserId={setSettingUserId}
        settingLlmModel={settingLlmModel}
        setSettingLlmModel={setSettingLlmModel}
        onSave={handleSaveSettings}
      />

      <style>{`
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
      `}</style>
    </div>
  );
}

export default App;
