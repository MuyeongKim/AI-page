"""Self-contained, offline HTML reports with explicit candidate-count semantics."""

import base64
import html
from collections import Counter
from datetime import datetime
from pathlib import Path

from mypackage.detection_records import (
    REVIEW_LABELS, asset_path, load_detections, read_record_json,
)
from mypackage.run_report import write_bytes_file

STATUS_LABELS = {
    "completed": "완료", "partial": "부분 완료", "failed": "실패", "cancelled": "취소",
    "disconnected": "입력 연결 끊김",
}


def escaped(value):
    return html.escape(str(value if value is not None else "확인되지 않음"), quote=True)


def embedded_thumbnail(folder, filename):
    path = asset_path(folder, filename)
    if path is None or not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        return "<p>확대 이미지 없음</p>"
    data = path.read_bytes()
    if not data.startswith(b"\xff\xd8"):
        return "<p>지원하지 않는 확대 이미지</p>"
    encoded = base64.b64encode(data).decode("ascii")
    return f'<img alt="후보 주변 원본 확대" src="data:image/jpeg;base64,{encoded}">'


def create_search_report(record_path, summary=None):
    path = Path(record_path)
    document = load_detections(path)
    if summary is None:
        summary_path = path.parent / "run_summary.json"
        summary = read_record_json(summary_path) if summary_path.is_file() else {}
    photos = document["photos"]
    entries = sorted(((photo, candidate) for photo in photos for candidate in photo["people"]),
                     key=lambda entry: entry[1]["confidence"], reverse=True)
    counts = Counter(candidate["review"] for _, candidate in entries)
    cards, rows, notes = [], [], []
    for index, (photo, candidate) in enumerate(entries):
        gps = photo.get("gps")
        location = f"{gps['lat']:.6f}, {gps['lon']:.6f}" if gps else "없음"
        values = [candidate["id"], Path(photo.get("source", "")).name,
                  f"{candidate['confidence']:.1%}", REVIEW_LABELS[candidate["review"]],
                  photo.get("captured_at"), location]
        rows.append("<tr>" + "".join(f"<td>{escaped(value)}</td>" for value in values) + "</tr>")
        if index < 6:
            image = embedded_thumbnail(path.parent, candidate.get("thumbnail_file"))
            cards.append(f"<article>{image}<div><b>{escaped(candidate['id'])}</b>"
                         f"<p>{escaped(values[1])} · {escaped(values[2])}<br>"
                         f"{escaped(values[3])} · 촬영 위치 {escaped(location)}</p></div></article>")
    for photo in photos:
        for warning in photo.get("warnings", []):
            notes.append(f"{Path(photo.get('source', '')).name}: {warning}")
        if photo.get("error"):
            notes.append(photo["error"])
    for key in ("errors", "warnings"):
        notes.extend(summary.get(key, []))
    checks = " · ".join(f"{label} {counts[state]}" for state, label in REVIEW_LABELS.items())
    body = f"""
<h1>수색 후보 확인 보고</h1>
<p>생성 {escaped(datetime.now().astimezone().isoformat(timespec='seconds'))} ·
버전 {escaped(document.get('app_version'))} ·
종료 상태 <strong>{escaped(STATUS_LABELS.get(summary.get('status', document.get('status')), '확인 필요'))}</strong></p>
<div class="notice">AI 후보를 사람이 확인하는 보조 자료입니다. 후보 수는 고유 인원이 아닙니다.
촬영 위치는 사진 GPS이며 사람의 정확한 좌표나 수색 완료를 뜻하지 않습니다. 확대는 원본 픽셀 표시입니다.</div>
<p>사진 기록 {len(photos)}장 · 처리 성공 {sum(p['status'] == 'completed' for p in photos)}장 ·
처리 실패 {sum(p['status'] == 'failed' for p in photos)}장 · 사람 후보 {len(entries)}건</p>
<p>{escaped(checks)}</p>
<p>모델 {escaped(summary.get('model'))} · 해상도 {escaped(summary.get('image_size'))} ·
최소 신뢰도 {escaped(summary.get('confidence'))} · 장치 {escaped(summary.get('device'))} ·
소요 시간(초) {escaped(summary.get('execution_time'))}</p>
<h2>신뢰도순 후보 요약</h2><p>상위 {min(6, len(entries))}건 이미지. 전체 {len(entries)}건은 아래 부록 표에 있습니다.</p>
<div class="cards">{''.join(cards) if cards else '<p>기록된 사람 후보가 없습니다. 처리 실패·미확인은 아래 주의 사항을 확인하세요.</p>'}</div>
<h2>오류·주의 사항</h2><ul>{''.join(f'<li>{escaped(note)}</li>' for note in dict.fromkeys(notes)) or '<li>기록된 오류·주의 사항 없음</li>'}</ul>
<section class="appendix"><h2>부록 · 전체 후보 {len(entries)}건</h2>
<table><thead><tr><th>후보 ID</th><th>사진</th><th>신뢰도</th><th>사람 확인</th><th>촬영 시각</th><th>촬영 위치</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></section>
"""
    return write_report_html(path.parent, body)


def write_report_html(folder, body):
    output = Path(folder) / "search_report.html"
    document = """<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="data:,">
<title>수색 후보 확인 보고</title><style>
*{box-sizing:border-box}body{font:14px/1.6 system-ui,'Malgun Gothic',sans-serif;color:#1f2937;
background:#f4efe7;margin:0;padding:28px}main{max-width:1000px;margin:auto;background:white;padding:28px}
h1{font-size:26px;color:#134e4a;margin:0 0 8px}h2{font-size:18px;margin:20px 0 8px}
p{overflow-wrap:anywhere}.notice{border-left:4px solid #0f766e;background:#edf6f2;padding:12px}
.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
article{display:flex;gap:10px;border:1px solid #c1d2ce;padding:8px;break-inside:avoid}
article img{width:100px;height:100px;object-fit:contain;background:#eee}article p{margin:4px 0}
table{width:100%;border-collapse:collapse;font-size:12px;table-layout:fixed}
th,td{text-align:left;border-bottom:1px solid #ddd;padding:6px;overflow-wrap:anywhere;vertical-align:top}
thead{display:table-header-group}tr{break-inside:avoid}
@media(max-width:600px){body{padding:8px}main{padding:12px}.cards{grid-template-columns:1fr}}
@page{size:A4;margin:14mm}@media print{body{padding:0;background:white;font-size:10pt}main{padding:0}
h1{font-size:18pt}h2{font-size:13pt}.appendix{break-before:page}article img{width:65px;height:65px}}
</style><main>""" + body + "</main></html>"
    write_bytes_file(output, document.encode("utf-8"))
    return output
