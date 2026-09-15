// Requires marked, DOMPurify, and MathJax to be loaded explicitly by the page.
export async function renderTeacherAnswer(root, value) {
  if (!window.marked || !window.DOMPurify || !window.MathJax?.typesetPromise) {
    throw new Error('Teacher answer renderers are unavailable');
  }

  const math = [];
  const svg = [];
  const holdMath = (content, display) => {
    math.push(display ? `\\[${content}\\]` : `\\(${content}\\)`);
    return `MATHPLACEHOLDER${math.length - 1}TOKEN`;
  };
  let source = String(value)
    .replace(/<svg\b[\s\S]*?<\/svg>/gi, block => {
      svg.push(block);
      return `SVGPLACEHOLDER${svg.length - 1}TOKEN`;
    })
    .replace(/\\\(([\s\S]*?)\\\)/g, (_, content) => holdMath(content, false))
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, content) => holdMath(content, true))
    .replace(/\$\$([\s\S]*?)\$\$/g, (_, content) => holdMath(content, true))
    .replace(/\$([^$\n]+?)\$/g, (_, content) => holdMath(content, false));

  const rendered = window.marked.parse(source, {gfm: true, breaks: true})
    .replace(/MATHPLACEHOLDER(\d+)TOKEN/g, (_, index) => math[Number(index)])
    .replace(/SVGPLACEHOLDER(\d+)TOKEN/g, (_, index) => svg[Number(index)]);
  const sanitized = window.DOMPurify.sanitize(rendered, {
    USE_PROFILES: {html: true, svg: true, svgFilters: true},
    FORBID_TAGS: ['foreignObject', 'script', 'animate', 'animateMotion', 'animateTransform', 'set'],
    FORBID_ATTR: ['onload', 'onclick', 'onerror'],
  });

  window.MathJax.typesetClear?.([root]);
  root.innerHTML = sanitized;
  root.querySelectorAll('a').forEach(link => {
    link.target = '_blank';
    link.rel = 'noopener';
  });
  await window.MathJax.typesetPromise([root]);
}
