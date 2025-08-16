// Configure backend URL: local vs production
const API_BASE =
  (location.hostname === 'localhost' || location.hostname === '127.0.0.1')
    ? 'http://localhost:4001'
    : 'https://YOUR-BACKEND-URL'; // <-- replace with your deployed FastAPI URL

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('detailedTripForm');
  const resultsDiv = document.getElementById('results');
  const loadingEl = document.getElementById('loadingIndicator');

  function getSelectedExperienceTypeIds() {
    return Array.from(document.querySelectorAll('input[name="experience"]:checked'))
      .map(cb => Number(cb.value))
      .filter(v => Number.isFinite(v));
  }

  async function fetchRecommendations(budget, duration, experienceTypes) {
    const res = await fetch(`${API_BASE}/api/cities`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      // The backend expects these exact keys
      body: JSON.stringify({
        budget: Number(budget),
        duration: Number(duration),
        experience_types: experienceTypes
      }),
    });

    // Handle common error formats from FastAPI
    if (!res.ok) {
      let detail = `Request failed: ${res.status}`;
      try {
        const err = await res.json();
        detail = err?.detail || err?.error || detail;
      } catch (_) {}
      throw new Error(detail);
    }
    return res.json();
  }

  function renderResults(list) {
    if (!Array.isArray(list) || list.length === 0) {
      resultsDiv.innerHTML = `
        <div class="card">
          <h4>No cities match your criteria</h4>
          <p class="text-muted">Try adjusting budget, duration, or place types.</p>
        </div>`;
      return;
    }

    const cards = list.map(city => {
      const types = (city.matching_types || []).join(', ');
      const score = (city.match_score ?? 0).toFixed(2);
      const name = city.name || 'Unknown';
      return `
        <div class="card">
          <h4>${name}</h4>
          <p><strong>Match Score:</strong> ${score}%</p>
          <p><strong>Matching Types:</strong> ${types || '—'}</p>
        </div>`;
    }).join('');

    resultsDiv.innerHTML = cards;
  }

  function setLoading(state) {
    loadingEl.classList.toggle('hidden', !state);
  }

  function validateInputs(budget, duration, experienceTypes) {
    if (!budget || Number(budget) < 0) return 'Please enter a valid budget.';
    if (!duration || Number(duration) <= 0) return 'Please enter a valid duration (days).';
    if (!experienceTypes.length) return 'Please select at least one place type.';
    return null;
    }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    resultsDiv.innerHTML = '';

    const budget = document.getElementById('budget').value.trim();
    const duration = document.getElementById('duration').value.trim();
    const experienceTypes = getSelectedExperienceTypeIds();

    const validationError = validateInputs(budget, duration, experienceTypes);
    if (validationError) {
      resultsDiv.innerHTML = `<div class="card"><p>${validationError}</p></div>`;
      return;
    }

    try {
      setLoading(true);
      const data = await fetchRecommendations(budget, duration, experienceTypes);
      renderResults(data);
    } catch (err) {
      resultsDiv.innerHTML = `<div class="card"><p>Error: ${err.message}</p></div>`;
    } finally {
      setLoading(false);
    }
  });
});
