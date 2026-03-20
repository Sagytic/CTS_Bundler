import dagre from 'dagre';

export const NODE_WIDTH = 220;
export const NODE_HEIGHT = 50;
export const RANK_SEP = 100;
export const NODE_SEP = 28;

/** 루트와 연결된 노드·엣지만 남기고, 동떨어진 노드/무리는 제거 */
export function keepConnectedToRoot(nodes, edges, rootId) {
  if (!nodes.length) return { nodes: [], edges: [] };
  const nodeIds = new Set(nodes.map((n) => n.id));
  const root = nodeIds.has(rootId) ? rootId : nodes[0].id;
  const adj = new Map();
  edges.forEach((e) => {
    if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) return;
    if (!adj.has(e.source)) adj.set(e.source, []);
    if (!adj.has(e.target)) adj.set(e.target, []);
    if (!adj.get(e.source).includes(e.target)) adj.get(e.source).push(e.target);
    if (!adj.get(e.target).includes(e.source)) adj.get(e.target).push(e.source);
  });
  const connected = new Set();
  const queue = [root];
  connected.add(root);
  while (queue.length) {
    const u = queue.shift();
    (adj.get(u) || []).forEach((v) => {
      if (connected.has(v)) return;
      connected.add(v);
      queue.push(v);
    });
  }
  const outNodes = nodes.filter((n) => connected.has(n.id));
  const outEdges = edges.filter((e) => connected.has(e.source) && connected.has(e.target));
  return { nodes: outNodes, edges: outEdges };
}

/** 무방향 BFS로 루트부터 레벨(0,1,2,3…)을 구해 3~4단계 계층으로 배치 */
export function getLayoutedElementsByLevel(nodes, edges, rootId, direction = 'LR') {
  const nodeIds = new Set(nodes.map((n) => n.id));
  const adj = new Map();
  edges.forEach((e) => {
    if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) return;
    if (!adj.has(e.source)) adj.set(e.source, []);
    if (!adj.has(e.target)) adj.set(e.target, []);
    if (!adj.get(e.source).includes(e.target)) adj.get(e.source).push(e.target);
    if (!adj.get(e.target).includes(e.source)) adj.get(e.target).push(e.source);
  });
  const level = new Map();
  const queue = [];
  if (nodeIds.has(rootId)) {
    level.set(rootId, 0);
    queue.push(rootId);
  } else if (nodes.length > 0) {
    const first = nodes[0].id;
    level.set(first, 0);
    queue.push(first);
  }
  while (queue.length) {
    const u = queue.shift();
    (adj.get(u) || []).forEach((v) => {
      if (level.get(v) != null) return;
      level.set(v, level.get(u) + 1);
      queue.push(v);
    });
  }
  const maxReached = level.size ? Math.max(...level.values()) : 0;
  nodes.forEach((n) => { if (level.get(n.id) == null) level.set(n.id, maxReached + 1); });

  const byLevel = new Map();
  nodes.forEach((n) => {
    const L = level.get(n.id) ?? 0;
    if (!byLevel.has(L)) byLevel.set(L, []);
    byLevel.get(L).push(n);
  });
  const maxLevel = Math.max(0, ...byLevel.keys());
  const sortedLevels = [...Array(maxLevel + 1).keys()];

  sortedLevels.forEach((L) => {
    const list = byLevel.get(L) || [];
    list.sort((a, b) => a.id.localeCompare(b.id));
    const totalH = list.length * (NODE_HEIGHT + NODE_SEP) - NODE_SEP;
    let y = -totalH / 2 + NODE_HEIGHT / 2;
    list.forEach((node) => {
      node.position = direction === 'LR' ? { x: L * (NODE_WIDTH + RANK_SEP), y } : { x: y, y: L * (NODE_HEIGHT + RANK_SEP) };
      node.targetPosition = direction === 'LR' ? 'left' : 'top';
      node.sourcePosition = direction === 'LR' ? 'right' : 'bottom';
      y += NODE_HEIGHT + NODE_SEP;
    });
  });

  return { nodes, edges };
}

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

export function getLayoutedElements(nodes, edges, direction = 'LR', rootId = null) {
  if (rootId) return getLayoutedElementsByLevel(nodes, edges, rootId, direction);

  dagreGraph.setGraph({ rankdir: direction, nodesep: 22, ranksep: 85, edgesep: 14, align: 'UL', ranker: 'longest-path' });
  nodes.forEach((node) => { dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT }); });
  edges.forEach((edge) => { dagreGraph.setEdge(edge.source, edge.target); });
  dagre.layout(dagreGraph);
  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = 'left'; node.sourcePosition = 'right';
    node.position = { x: nodeWithPosition.x - NODE_WIDTH / 2, y: nodeWithPosition.y - NODE_HEIGHT / 2 };
    return node;
  });
  return { nodes, edges };
}
