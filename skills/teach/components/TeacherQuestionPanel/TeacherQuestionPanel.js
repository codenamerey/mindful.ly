/* Reusable mount helper. Host supplies API adapters; this module owns the canonical DOM. */
export async function loadTeacherRenderers() {
  const load = (id, src, ready) => ready() ? Promise.resolve() : new Promise((resolve, reject) => {
    const existing = document.getElementById(id);
    if (existing) { existing.addEventListener('load', resolve, {once:true}); existing.addEventListener('error', reject, {once:true}); return; }
    const script = document.createElement('script'); script.id = id; script.src = src; script.onload = resolve; script.onerror = reject; document.head.appendChild(script);
  });
  await Promise.all([
    load('teacher-marked', 'https://cdn.jsdelivr.net/npm/marked/lib/marked.umd.js', () => Boolean(window.marked)),
    load('teacher-dompurify', 'https://cdn.jsdelivr.net/npm/dompurify@3/dist/purify.min.js', () => Boolean(window.DOMPurify)),
  ]);
  if (!window.MathJax?.typesetPromise) {
    window.MathJax = {tex:{inlineMath:[['$', '$'], ['\\(', '\\)']]}};
    await load('teacher-mathjax', 'https://cdn.jsdelivr.net/npm/mathjax@4/tex-chtml.js', () => Boolean(window.MathJax?.typesetPromise));
  }
  await window.MathJax.startup?.promise;
}

export function renderTeacherMarkdown(value) {
  if (!window.marked || !window.DOMPurify) throw new Error('Teacher Markdown renderer is unavailable');
  const math = [];
  const source = String(value).replace(/\$\$([\s\S]*?)\$\$/g, (_, body) => { math.push(`\\[${body}\\]`); return `MATHPLACEHOLDER${math.length-1}TOKEN`; })
    .replace(/\$([^$\n]+?)\$/g, (_, body) => { math.push(`\\(${body}\\)`); return `MATHPLACEHOLDER${math.length-1}TOKEN`; });
  const html = window.marked.parse(source, {gfm:true, breaks:true}).replace(/MATHPLACEHOLDER(\d+)TOKEN/g, (_, index) => math[Number(index)]);
  return window.DOMPurify.sanitize(html, {USE_PROFILES:{html:true,svg:true,svgFilters:true},FORBID_TAGS:['foreignObject','script','animate','animateMotion','animateTransform','set'],FORBID_ATTR:['onload','onclick','onerror']});
}

export function mountTeacherQuestionPanel({lessonId, apiBase = '/api/questions', eventsUrl = '/api/events', renderAnswer = renderTeacherMarkdown}) {
  if (!lessonId) return null;
  const section = document.createElement('section');
  section.className = 'teacher-qa';
  section.innerHTML = `<h2>Ask the teacher</h2><div class="teacher-qa-history" aria-live="polite"></div><form class="teacher-qa-form"><textarea maxlength="4000" aria-label="Question for the teacher" placeholder="Ask about this lesson"></textarea><div class="teacher-qa-attachments" aria-live="polite"></div><div class="teacher-qa-file-row"><label class="teacher-qa-file-button">Attach images<input type="file" accept="image/png,image/jpeg,image/gif,image/webp,image/bmp" multiple hidden></label><span>or paste screenshots with Ctrl+V</span></div><div class="teacher-qa-actions"><button class="teacher-qa-submit" type="submit">Ask teacher</button></div></form>`;
  const nav = document.querySelector('.lesson-nav');
  (nav || document.body).insertAdjacentElement(nav ? 'beforebegin' : 'beforeend', section);
  // Hosts must implement: five-image merging/removal, backend validation, sanitized history
  // rendering, submit pending state, SSE reload, and MathJax re-typesetting per SKILL.md.
  section.dataset.lessonId = lessonId;
  section.dataset.apiBase = apiBase;
  section.dataset.eventsUrl = eventsUrl;
  section.renderTeacherAnswer = renderAnswer;
  return section;
}
