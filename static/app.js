(() => {
  const input = document.getElementById('noticeInput');
  const form = document.getElementById('analyzeForm');
  const analyzeButton = document.getElementById('analyzeButton');
  const sampleButton = document.getElementById('sampleButton');
  const charCount = document.getElementById('charCount');
  const resultsSection = document.getElementById('resultsSection');
  const toast = document.getElementById('toast');
  let lastResults = null;
  let activeFilter = 'All';
  let toastTimer = null;

  const sampleNotice = `NextSpark Hacks — Rules and Submission Requirements\n\nDeadline: 27 Oct 2026 @ 8:30am GMT+5:30. Submit everything before the deadline.\n\nEligibility: Participants must meet the age, location, and other eligibility requirements. Ages 13+ only. Students only. Companies and professional organizations are excluded from participation. You may participate individually or in a team of up to four people.\n\nWhat to build: Build a working prototype that addresses a real-world problem. Projects must be created during the official submission period. Existing libraries, frameworks, APIs, and publicly available assets are allowed when used according to their licenses and properly credited.\n\nWhat to submit: The Devpost submission must include a project description, a public source-code repository with setup instructions, a 1–3 minute demo video accessible to judges, at least one project screenshot, and a list of technologies, resources, and AI assistance used. A live demo link is encouraged but optional. Clearly identify incomplete features and simulated functionality.\n\nAI tools: AI tools may be used for coding, design, research, or other development tasks. Explain how you used them in your submission and distinguish your contributions from generated or pre-existing work.\n\nRestrictions: Do not include passwords, API keys, private information, or materials you are not authorized to share. Plagiarism, false claims, judging manipulation, and misrepresenting team contributions may result in disqualification. Organizers and judges may not compete for prizes.\n\nJudging criteria: Projects will be evaluated on creativity and originality, impact, technical execution, and design and user experience. Projects will be judged on what is demonstrated and submitted, rather than promised future features.\n\nPrizes: First place receives $100 cash and a certificate. Other prizes include credits or subscriptions; verify the official page for current prize details and conditions.`;

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 2500);
  }
  function escapeHTML(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  }
  input.addEventListener('input', () => { charCount.textContent = `${input.value.length.toLocaleString()} / 50,000`; });
  sampleButton.addEventListener('click', () => {
    input.value = sampleNotice;
    charCount.textContent = `${input.value.length.toLocaleString()} / 50,000`;
    input.focus();
    showToast('Sample notice loaded — analyze it to see the readout.');
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (input.value.trim().length < 20) { showToast('Paste a little more source text first.'); input.focus(); return; }
    analyzeButton.disabled = true;
    analyzeButton.querySelector('span:first-child').textContent = 'Reading the notice…';
    try {
      const response = await fetch('/api/analyze', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({notice:input.value})});
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || 'Something went wrong.');
      lastResults = payload.results;
      activeFilter = 'All';
      renderResults(lastResults);
      resultsSection.classList.remove('hidden');
      resultsSection.scrollIntoView({behavior:'smooth', block:'start'});
      showToast('Readout ready. Verify every finding against the source.');
    } catch (err) {
      showToast(err.message || 'Could not analyze this notice. Please try again.');
    } finally {
      analyzeButton.disabled = false;
      analyzeButton.querySelector('span:first-child').textContent = 'Analyze notice';
    }
  });

  function renderResults(data) {
    document.getElementById('summaryText').textContent = data.summary;
    document.getElementById('findingTotal').textContent = data.findings.length;
    document.getElementById('dateTotal').textContent = data.dates.length;
    document.getElementById('nextDate').textContent = data.dates.length ? (data.dates[0].likely_deadline ? `Deadline wording: ${data.dates[0].raw}` : `First date: ${data.dates[0].raw}`) : 'No date parsed yet';
    renderMiniBars(data.counts);
    renderFilters(data.findings);
    renderFindings(data.findings);
    renderDates(data.dates);
    renderChecklist(data);
    renderReviewPrompts(data.review_prompts);
    document.getElementById('methodNote').textContent = data.method;
  }
  function renderMiniBars(counts) {
    const element = document.getElementById('miniBars');
    const values = Object.entries(counts).filter(([,value])=>value>0).sort((a,b)=>b[1]-a[1]).slice(0,7);
    const total = Math.max(1, ...values.map(([,v])=>v));
    element.innerHTML = values.length ? values.map(([key,value])=>`<span class="mini-bar" title="${escapeHTML(key)}: ${value}" style="width:${Math.max(8,(value/total)*48)}px"></span>`).join('') : '<span class="count-caption">No matched categories yet</span>';
  }
  function renderFilters(findings) {
    const labels = ['All', ...new Set(findings.map(f=>f.category))];
    const box = document.getElementById('categoryFilters');
    box.innerHTML = labels.map(label=>`<button type="button" class="filter-chip ${label===activeFilter?'active':''}" data-filter="${escapeHTML(label)}">${escapeHTML(label)}${label==='All'?'':` · ${findings.filter(f=>f.category===label).length}`}</button>`).join('');
    box.querySelectorAll('button').forEach(button=>button.addEventListener('click',()=>{
      activeFilter = button.dataset.filter;
      renderFilters(lastResults.findings);
      renderFindings(lastResults.findings);
    }));
  }
  function renderFindings(findings) {
    const filtered = activeFilter==='All' ? findings : findings.filter(f=>f.category===activeFilter);
    document.getElementById('filterCount').textContent = `${filtered.length} item${filtered.length===1?'':'s'}`;
    const list = document.getElementById('findingsList');
    const empty = document.getElementById('emptyFindings');
    list.innerHTML = filtered.map((finding,index)=>`<article class="finding-card"><div class="finding-top"><span class="category-tag tag-${escapeHTML(finding.style)}">${escapeHTML(finding.category)}</span><span class="evidence-mark">EVIDENCE / ${String(index+1).padStart(2,'0')}</span></div><p class="finding-evidence">${escapeHTML(finding.evidence)}</p><p class="finding-note">${escapeHTML(finding.note)}</p></article>`).join('');
    empty.classList.toggle('hidden', filtered.length>0);
  }
  function renderDates(dates) {
    const list = document.getElementById('datesList');
    if (!dates.length) { list.innerHTML = '<div class="empty-state">No recognizable dates found. Check the original schedule manually.</div>'; return; }
    list.innerHTML = dates.map(item=>`<article class="date-item"><strong>${escapeHTML(item.raw)}</strong><span class="date-timing">${escapeHTML(item.timing)}${item.likely_deadline?' · deadline wording nearby':''}</span><div class="date-context">${escapeHTML(item.context)}</div></article>`).join('');
  }
  function renderChecklist(data) {
    const checklist = document.getElementById('checklist');
    const items = [
      'Verify the deadline, time and time zone',
      'Confirm eligibility and team-size rules',
      'Check every required submission item',
      'Read restrictions and disqualification clauses',
      'Credit AI tools and external resources used',
      'Test all links and demo access before submitting'
    ];
    checklist.innerHTML = items.map((item,i)=>`<label class="check-item"><input type="checkbox" data-check="${i}"><span>${escapeHTML(item)}</span></label>`).join('');
    checklist.querySelectorAll('input').forEach(box=>box.addEventListener('change', updateProgress));
    updateProgress();
  }
  function updateProgress() {
    const boxes = [...document.querySelectorAll('#checklist input')];
    const checked = boxes.filter(box=>box.checked).length;
    document.getElementById('checkProgress').textContent = `${checked} / ${boxes.length}`;
    document.getElementById('checkProgressFill').style.width = `${boxes.length ? checked/boxes.length*100 : 0}%`;
    boxes.forEach(box=>box.closest('.check-item').classList.toggle('done',box.checked));
  }
  function renderReviewPrompts(prompts) {
    const panel = document.getElementById('reviewPromptsPanel');
    const box = document.getElementById('reviewPrompts');
    box.innerHTML = prompts.map(p=>`<span class="review-chip" title="${escapeHTML(p.reason)}">${escapeHTML(p.label)}</span>`).join('');
    panel.classList.toggle('hidden',prompts.length===0);
  }

  document.getElementById('exportButton').addEventListener('click', async () => {
    if (!lastResults) return;
    try {
      const res = await fetch('/export.csv', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(lastResults)});
      if (!res.ok) throw new Error('Export failed.');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href=url; a.download='claritykit-findings.csv'; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
      showToast('CSV exported.');
    } catch { showToast('Could not export CSV. Try again.'); }
  });
  document.getElementById('copyButton').addEventListener('click', async () => {
    if (!lastResults) return;
    const lines = ['CLARITYKIT — NOTICE READOUT', '', lastResults.summary, '', 'FINDINGS', ...lastResults.findings.map(f=>`[${f.category}] ${f.evidence}\n${f.note}`), '', 'DATES', ...lastResults.dates.map(d=>`${d.raw} — ${d.timing}\n${d.context}`), '', 'LIMITATION', lastResults.method];
    try { await navigator.clipboard.writeText(lines.join('\n')); showToast('Summary copied to clipboard.'); }
    catch { showToast('Clipboard access was blocked by this browser.'); }
  });
})();
