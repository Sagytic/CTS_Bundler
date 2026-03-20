export function formatTime(timeStr) {
  if (!timeStr || timeStr.length !== 6) return timeStr;
  return `${timeStr.slice(0, 2)}:${timeStr.slice(2, 4)}:${timeStr.slice(4, 6)}`;
}

export function filterMainTransports(transports) {
  return transports.filter((tr) => {
    const trType = String(tr.TRFUNCTION || tr.trfunction || '').toUpperCase();
    return trType === 'K' || trType === 'W';
  });
}

/** 메인 TR + 하위 태스크 오브젝트를 유형별로 묶어서 반환 */
export function getTrObjectsTree(parentTrKorr, rawTrData) {
  const parent = rawTrData.find((tr) => (tr.TRKORR || tr.trkorr) === parentTrKorr);
  const children = rawTrData.filter((tr) => (tr.STRKORR || tr.strkorr) === parentTrKorr);
  let allObjs = [];
  if (parent) allObjs = [...(parent.objects || parent.OBJECTS || [])];
  children.forEach((child) => {
    allObjs = [...allObjs, ...(child.objects || child.OBJECTS || [])];
  });
  const grouped = {};
  allObjs.forEach((obj) => {
    const type = obj.OBJECT || obj.object || 'UNKNOWN';
    const name = obj.OBJ_NAME || obj.obj_name || 'Unnamed';
    if (!grouped[type]) grouped[type] = new Set();
    grouped[type].add(name);
  });
  return grouped;
}
