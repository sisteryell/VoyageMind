    /* =========================================================
       VoyageMind — vanilla JS
    ========================================================= */

    marked.setOptions({ breaks: true, gfm: true });

    /*  helpers  */
    function esc(s) {
      return String(s ?? '')
        .replace(/&/g,'&amp;').replace(/</g,'&lt;')
        .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    /** Strip any leading non-letter/non-digit characters the LLM sometimes adds (•, â€¢, -, *, etc.) */
    function cleanActivity(s) {
      return String(s ?? '').replace(/^[^\p{L}\p{N}]+/u, '').trim();
    }

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 2500);
    }

    function showError(id, msg) {
      const el = document.getElementById(id);
      el.textContent = msg;
      el.classList.toggle('visible', !!msg);
    }

    /*  tab switching  */
    function switchTab(name) {
      document.querySelectorAll('.tab-btn').forEach(b =>
        b.classList.toggle('active', b.dataset.tab === name));
      document.querySelectorAll('.tab-content').forEach(c =>
        c.classList.toggle('active', c.id === 'tab-' + name));
    }

    /*  style chip toggle  */
    function toggleStyle(el) { el.classList.toggle('selected'); }

    function getStyles(chipContainerId) {
      return [...document.querySelectorAll('#' + chipContainerId + ' .style-chip.selected')]
        .map(c => c.dataset.style);
    }

    /*  step animation  */
    const STYLE_META = {
      adventure:  { emoji: '\u{1F3D4}', label: 'Adventure'  },
      relaxation: { emoji: '\u{1F334}', label: 'Relaxation' },
      family:     { emoji: '\u{1F46A}', label: 'Family'     },
      honeymoon:  { emoji: '\u{1F498}', label: 'Honeymoon'  },
      solo:       { emoji: '\u{1F6B6}', label: 'Solo'       },
      culture:    { emoji: '\u{1F3DB}', label: 'Culture'    },
      food:       { emoji: '\u{1F35C}', label: 'Food'       },
      nature:     { emoji: '\u{1F33F}', label: 'Nature'     },
      aggregate:  { emoji: '\u{1F3AF}', label: 'Aggregate'  },
      itinerary:  { emoji: '\u{1F4C5}', label: 'Itinerary'  },
    };

    let _stepTimer = null;
    function startSteps(styles) {
      // Build the step list: selected style agents + always Aggregate + Itinerary
      const agentKeys = (styles && styles.length ? styles : Object.keys(STYLE_META).slice(0, 8));
      const steps     = [...agentKeys, 'aggregate', 'itinerary'];

      // Render pills dynamically
      const container = document.getElementById('stepsContainer');
      container.innerHTML = steps.map((key, i) => {
        const m = STYLE_META[key] || { emoji: '\u2699', label: key };
        return `<span class="step-pill" data-step="${i}">${m.emoji} ${m.label}</span>`;
      }).join('');

      const pills = container.querySelectorAll('.step-pill');
      const txt   = document.getElementById('loadingText');
      if (pills[0]) pills[0].classList.add('active');
      txt.textContent = `Running ${STYLE_META[steps[0]]?.label ?? steps[0]} agent\u2026`;
      let i = 1;
      _stepTimer = setInterval(() => {
        if (i < pills.length) {
          pills[i - 1].classList.replace('active', 'done');
          pills[i - 1].classList.replace('active', 'done');
          pills[i].classList.add('active');
          txt.textContent = i < steps.length - 2
            ? `Running ${STYLE_META[steps[i]]?.label ?? steps[i]} agent\u2026`
            : i === steps.length - 2
              ? 'Aggregating final picks\u2026'
              : 'Building itineraries\u2026';
          i++;
        } else {
          clearInterval(_stepTimer);
        }
      }, 3200);
    }
    function stopSteps() { clearInterval(_stepTimer); }

    /* ========================================================= */
    /*  PLAN TRAVEL                                               */
    /* ========================================================= */
    let _lastPlan = null;

    async function planTravel() {
      const country  = document.getElementById('country').value.trim();
      const budget   = document.getElementById('budget').value;
      const duration = (v => Number.isNaN(v) ? 5 : v)(parseInt(document.getElementById('duration').value, 10));
      const cityCount = (v => Number.isNaN(v) ? 2 : Math.min(5, Math.max(1, v)))(parseInt(document.getElementById('cityCount').value, 10));
      const styles   = getStyles('styleChips');

      showError('errorBanner', '');
      if (!country) { showError('errorBanner', 'Please enter a country name.'); return; }

      document.getElementById('resultsSection').classList.remove('visible');
      document.getElementById('chatSection').classList.remove('visible');
      document.getElementById('loadingState').classList.add('visible');
      startSteps(styles);

      try {
        const res  = await fetch('/plan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ country, budget, duration, city_count: cityCount, travel_styles: styles }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Request failed');
        _lastPlan = data;
        renderResults(data);
      } catch(e) {
        showError('errorBanner', e.message);
      } finally {
        stopSteps();
        document.getElementById('loadingState').classList.remove('visible');
      }
    }

    /*  render results  */
    function renderResults(data) {
      document.getElementById('resCountry').textContent = data.country;

      // meta pills
      const meta = document.getElementById('resMeta');
      meta.innerHTML =
        `<span class="meta-pill">${esc(data.budget)} budget</span>` +
        `<span class="meta-pill">${esc(data.duration)} days</span>` +
        `<span class="meta-pill">${esc(data.city_count || (data.recommendations || []).length)} cities</span>` +
        (data.travel_styles||[]).map(s => `<span class="meta-pill">${esc(s)}</span>`).join('');

      // rec cards
      const grid = document.getElementById('recGrid');
      grid.innerHTML = (data.recommendations||[]).map((r, i) => `
        <div class="rec-card">
          <div class="rec-rank">${i + 1}</div>
          <div class="rec-city">${esc(r.city)}</div>
          <div class="rec-reason">${esc(r.reason)}</div>
        </div>`).join('');

      // itineraries
      const iSec = document.getElementById('itinerarySection');
      if (data.itineraries && data.itineraries.length) {
        iSec.innerHTML = '<h3>&#128197; Day-by-Day Itineraries</h3>' +
          data.itineraries.map(it => `
            <div class="agent-panel open">
              <div class="agent-header" onclick="this.parentElement.classList.toggle('open')">
                <span>&#128205;</span>
                <span class="itin-city">${esc(it.city)}</span>
                <span class="chevron">&#9660;</span>
              </div>
              <div class="agent-body">
                <div class="agent-body-inner">
                  ${(it.days||[]).map(d => `
                    <div class="day-card">
                      <div class="day-title">Day ${d.day}: ${esc(d.title)}</div>
                      <ul class="day-activities">
                        ${(d.activities||[]).map(a => `<li>${esc(a.replace(/^[\s\u2022\u00B7\-\*]+/, ''))}</li>`).join('')}
                      </ul>
                    </div>`).join('')}
                </div>
              </div>
            </div>`).join('');
      } else {
        iSec.innerHTML = '';
      }

      // agent breakdown — built dynamically from whatever agents actually ran
      const AGENT_COLORS = ['#a78bfa','#fb923c','#38bdf8','#4ade80','#f472b6','#facc15','#34d399','#60a5fa'];
      const dSec = document.getElementById('detailsSection');
      const agentEntries = Object.entries(data.agent_details || {});
      dSec.innerHTML = agentEntries.length
        ? '<h3>&#128202; Agent Breakdown</h3>' +
          agentEntries.map(([key, cities], idx) => {
            const meta  = STYLE_META[key] || { emoji: '\u2699\uFE0F', label: key };
            const color = AGENT_COLORS[idx % AGENT_COLORS.length];
            return `
              <div class="agent-panel open">
                <div class="agent-header" onclick="this.parentElement.classList.toggle('open')">
                  <span class="agent-icon">${meta.emoji}</span>
                  <span class="agent-title">${meta.label}</span>
                  <span class="chevron">&#9660;</span>
                </div>
                <div class="agent-body">
                  <div class="agent-body-inner">
                    ${(cities||[]).map(c => {
                      const pct = Math.round((c.confidence_score || 0) * 100);
                      return `
                        <div class="city-row">
                          <span class="city-name">${esc(c.city)}</span>
                          <div class="confidence-bar-wrapper">
                            <div class="confidence-bar" style="width:${pct}%;background:${color}"></div>
                          </div>
                          <span class="confidence-label">${pct}%</span>
                          <span class="city-reason">${esc(c.reason)}</span>
                        </div>`;
                    }).join('')}
                  </div>
                </div>
              </div>`;
          }).join('')
        : '';

      document.getElementById('resultsSection').classList.add('visible');
      document.getElementById('chatSection').classList.add('visible');
      document.getElementById('chatMessages').innerHTML = '';
    }

    /* ========================================================= */
    /*  CHAT                                                      */
    /* ========================================================= */
    async function sendChat() {
      const input = document.getElementById('chatInput');
      const q     = input.value.trim();
      if (!q || !_lastPlan) return;

      const msgs = document.getElementById('chatMessages');

      // user bubble
      msgs.insertAdjacentHTML('beforeend',
        `<div class="chat-msg user">${esc(q)}</div>`);
      input.value = '';

      // typing indicator
      const typingId = 'typing-' + Date.now();
      msgs.insertAdjacentHTML('beforeend',
        `<div class="chat-msg assistant typing" id="${typingId}">Thinking&hellip;</div>`);
      msgs.scrollTop = msgs.scrollHeight;

      try {
        const res  = await fetch('/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            country:         _lastPlan.country,
            question:        q,
            budget:          _lastPlan.budget,
            duration:        _lastPlan.duration,
            travel_styles:   _lastPlan.travel_styles,
            recommendations: _lastPlan.recommendations,
          }),
        });
        const data = await res.json();
        document.getElementById(typingId)?.remove();
        if (!res.ok) throw new Error(data.detail || 'Chat error');
        // render markdown for assistant reply
        const bubble = document.createElement('div');
        bubble.className = 'chat-msg assistant chat-md';
        bubble.innerHTML = marked.parse(data.answer);
        msgs.appendChild(bubble);
      } catch(e) {
        const el = document.getElementById(typingId);
        if (el) { el.className = 'chat-msg assistant'; el.textContent = 'Error: ' + e.message; }
      } finally {
        msgs.scrollTop = msgs.scrollHeight;
      }
    }

    /* ========================================================= */
    /*  COMPARE                                                   */
    /* ========================================================= */
    async function compareCountries() {
      const cA  = document.getElementById('countryA').value.trim();
      const cB  = document.getElementById('countryB').value.trim();
      const bud = document.getElementById('compareBudget').value;
      const dur = (v => Number.isNaN(v) ? 5 : v)(parseInt(document.getElementById('compareDuration').value, 10));
      const sty = getStyles('compareStyleChips');

      showError('compareError', '');
      if (!cA || !cB) { showError('compareError', 'Please enter both country names.'); return; }

      document.getElementById('compareGrid').innerHTML = '';
      document.getElementById('compareLoading').classList.add('visible');

      try {
        const res  = await fetch('/compare', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ country_a: cA, country_b: cB, budget: bud, duration: dur, travel_styles: sty }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Compare failed');
        renderCompare(data);
      } catch(e) {
        showError('compareError', e.message);
      } finally {
        document.getElementById('compareLoading').classList.remove('visible');
      }
    }

    function renderCompare(data) {
      const renderCol = (plan, accentColor) => `
        <div class="compare-col">
          <h3 style="border-bottom-color:${accentColor}">&#127757; ${esc(plan.country)}</h3>
          ${(plan.recommendations||[]).map(r => `
            <div class="compare-city">
              <div class="compare-city-name">${esc(r.city)}</div>
              <div class="compare-city-reason">${esc(r.reason)}</div>
            </div>`).join('')}
          ${(plan.itineraries||[]).map(it => `
            <h4 style="margin:.8rem 0 .4rem;font-size:.9rem;color:var(--accent2)">
              &#128197; ${esc(it.city)} Itinerary
            </h4>
            ${(it.days||[]).map(d => `
              <div class="compare-itin-day">
                <strong>Day ${d.day}: ${esc(d.title)}</strong>
                <ul>${(d.activities||[]).map(a => `<li>${esc(cleanActivity(a))}</li>`).join('')}</ul>
              </div>`).join('')}`).join('')}
        </div>`;

      document.getElementById('compareGrid').innerHTML =
        renderCol(data.country_a, 'var(--accent)') +
        renderCol(data.country_b, 'var(--accent3)');
    }

    /* ========================================================= */
    /*  SHARE                                                     */
    /* ========================================================= */
    function shareResults() {
      if (!_lastPlan) return;
      const p = new URLSearchParams({
        country:  _lastPlan.country,
        budget:   _lastPlan.budget,
        duration: _lastPlan.duration,
        city_count: _lastPlan.city_count || (_lastPlan.recommendations?.length || 2),
      });
      if (_lastPlan.travel_styles?.length) p.set('styles', _lastPlan.travel_styles.join(','));
      const url = location.origin + '?' + p.toString();
      navigator.clipboard.writeText(url)
        .then(() => showToast('Link copied!'))
        .catch(() => prompt('Share this link:', url));
    }

    /*  keyboard shortcuts  */
    document.getElementById('country').addEventListener('keydown', e => {
      if (e.key === 'Enter') planTravel();
    });
    document.getElementById('chatInput').addEventListener('keydown', e => {
      if (e.key === 'Enter') sendChat();
    });

    /*  URL auto-fill (share links)  */
    (() => {
      const p = new URLSearchParams(location.search);
      if (!p.has('country')) return;
      document.getElementById('country').value  = p.get('country');
      if (p.has('budget'))   document.getElementById('budget').value    = p.get('budget');
      if (p.has('duration')) document.getElementById('duration').value  = p.get('duration');
      if (p.has('city_count')) document.getElementById('cityCount').value = p.get('city_count');
      if (p.has('styles')) {
        const styles = p.get('styles').split(',');
        document.querySelectorAll('#styleChips .style-chip').forEach(c => {
          if (styles.includes(c.dataset.style)) c.classList.add('selected');
        });
      }
      setTimeout(() => planTravel(), 300);
    })();
