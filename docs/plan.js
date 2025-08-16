// Configure backend URL: local vs production
const API_BASE =
  (location.hostname === 'localhost' || location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'  // Updated to FastAPI default port
    : 'https://travel-recommendation-system-47mw.onrender.com';

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('detailedTripForm');
  const resultsDiv = document.getElementById('results');
  const loadingEl = document.getElementById('loadingIndicator');
  
  // Debug: confirm the exact URL being called (remove after testing)
  console.log('API_BASE:', API_BASE);

  function getSelectedExperienceTypeIds() {
    return Array.from(document.querySelectorAll('input[name="experience"]:checked'))
      .map(cb => Number(cb.value))
      .filter(v => Number.isFinite(v));
  }

  async function fetchRecommendations(budget, duration, experienceTypes) {
    const url = `${API_BASE}/api/cities`;
    
    // Debug: show full request URL
    console.log('Requesting:', url);
    console.log('Payload:', { budget: Number(budget), duration: Number(duration), experience_types: experienceTypes });

    // Create abort controller for timeout handling
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          budget: Number(budget),
          duration: Number(duration),
          experience_types: experienceTypes
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!res.ok) {
        let detail = `Request failed: ${res.status}`;
        try {
          const err = await res.json();
          detail = err?.detail || err?.error || detail;
        } catch (_) {
          // If we can't parse the error response, use the status text
          detail = `${res.status}: ${res.statusText}`;
        }
        throw new Error(detail);
      }

      return res.json();
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error.name === 'AbortError') {
        throw new Error('Request timed out. Please try again.');
      }
      
      // Network errors
      if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        throw new Error('Unable to connect to server. Please check your internet connection.');
      }
      
      throw error;
    }
  }

  function renderResults(list) {
    if (!Array.isArray(list) || list.length === 0) {
      resultsDiv.innerHTML = `
        <div class="card">
          <h4>No cities match your criteria</h4>
          <p class="text-muted">Try adjusting your budget, duration, or experience types to find more options.</p>
        </div>`;
      return;
    }

    const cards = list.map((city, index) => {
      const types = (city.matching_types || []).join(', ');
      const score = Number.isFinite(city.match_score) ? city.match_score.toFixed(2) : '0.00';
      const name = city.name || 'Unknown';
      
      // Add rank number for better UX
      const rank = index + 1;
      
      return `
        <div class="card">
          <div class="card-header">
            <h4>#${rank} - ${name}</h4>
            <span class="match-score">${score}% match</span>
          </div>
          <div class="card-body">
            <p><strong>Experience Types:</strong> ${types || 'No matching types found'}</p>
          </div>
        </div>`;
    }).join('');

    resultsDiv.innerHTML = cards;
  }

  function setLoading(state) {
    if (loadingEl) {
      loadingEl.classList.toggle('hidden', !state);
    }
    
    // Disable form during loading
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
      submitButton.disabled = state;
      submitButton.textContent = state ? 'Searching...' : 'Get Recommendations';
    }
  }

  function validateInputs(budget, duration, experienceTypes) {
    // Budget validation
    if (budget === '' || isNaN(Number(budget)) || Number(budget) < 0) {
      return 'Please enter a valid budget amount (must be a positive number).';
    }
    
    // Duration validation
    if (duration === '' || isNaN(Number(duration)) || Number(duration) <= 0) {
      return 'Please enter a valid duration (must be greater than 0 days).';
    }
    
    // Experience types validation
    if (!experienceTypes.length) {
      return 'Please select at least one experience type.';
    }
    
    // Additional reasonable limits
    if (Number(budget) > 1000000) {
      return 'Budget seems unusually high. Please enter a reasonable amount.';
    }
    
    if (Number(duration) > 365) {
      return 'Duration seems unusually long. Please enter a reasonable number of days.';
    }
    
    return null;
  }

  function showError(message) {
    resultsDiv.innerHTML = `
      <div class="card error">
        <h4>⚠️ Error</h4>
        <p>${message}</p>
        <p class="text-muted">Please try again or contact support if the problem persists.</p>
      </div>`;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    resultsDiv.innerHTML = '';

    const budget = document.getElementById('budget').value.trim();
    const duration = document.getElementById('duration').value.trim();
    const experienceTypes = getSelectedExperienceTypeIds();

    // Client-side validation
    const validationError = validateInputs(budget, duration, experienceTypes);
    if (validationError) {
      showError(validationError);
      return;
    }

    try {
      setLoading(true);
      console.log('Submitting request with:', { budget, duration, experienceTypes });
      
      const data = await fetchRecommendations(budget, duration, experienceTypes);
      console.log('Received response:', data);
      
      renderResults(data);
    } catch (err) {
      console.error('Request failed:', err);
      showError(err.message);
    } finally {
      setLoading(false);
    }
  });

  // Optional: Add real-time validation feedback
  const budgetInput = document.getElementById('budget');
  const durationInput = document.getElementById('duration');
  
  if (budgetInput) {
    budgetInput.addEventListener('input', (e) => {
      const value = e.target.value;
      if (value && (isNaN(Number(value)) || Number(value) < 0)) {
        e.target.setCustomValidity('Please enter a valid positive number');
      } else {
        e.target.setCustomValidity('');
      }
    });
  }
  
  if (durationInput) {
    durationInput.addEventListener('input', (e) => {
      const value = e.target.value;
      if (value && (isNaN(Number(value)) || Number(value) <= 0)) {
        e.target.setCustomValidity('Please enter a number greater than 0');
      } else {
        e.target.setCustomValidity('');
      }
    });
  }
});
