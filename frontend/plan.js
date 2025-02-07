
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('detailedTripForm');
    const resultsDiv = document.getElementById('results');
    const placeTypesCheckboxes = document.getElementById('placeTypesCheckboxes');
    const loadingIndicator = document.createElement('div');
    loadingIndicator.id = 'loadingIndicator';
    loadingIndicator.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="sr-only">Loading...</span></div>';
    loadingIndicator.style.display = 'none';
    form.appendChild(loadingIndicator);

    // Populate place types checkboxes
    const placeTypes = [
        {id: 1, name: 'Beach Escapes', icon: 'fa-umbrella-beach'},
        {id: 2, name: 'Mountain Retreats', icon: 'fa-mountain'},
        {id: 3, name: 'Cultural Hotspots', icon: 'fa-landmark'},
        {id: 4, name: 'Historical Journeys', icon: 'fa-monument'},
        {id: 5, name: 'Natural Wonders', icon: 'fa-tree'},
        {id: 6, name: 'Adventure Activities', icon: 'fa-hiking'},
        {id: 7, name: 'Wildlife Encounters', icon: 'fa-paw'},
        {id: 8, name: 'Spiritual Experiences', icon: 'fa-pray'},
        {id: 9, name: 'Festivals and Celebrations', icon: 'fa-music'},
        {id: 10, name: 'Urban Nightlife', icon: 'fa-city'},
        {id: 11, name: 'Culinary Adventures', icon: 'fa-utensils'},
        {id: 12, name: 'Recreational Parks', icon: 'fa-leaf'},
        {id: 13, name: 'Scenic Views', icon: 'fa-camera'},
        {id: 14, name: 'Cave Exploration', icon: 'fa-dungeon'},
        {id: 15, name: 'Forest Activities', icon: 'fa-tree'},
        {id: 16, name: 'Aquatic Adventures', icon: 'fa-water'},
        {id: 17, name: 'Family-Friendly Activities', icon: 'fa-child'}
    ];

    placeTypes.forEach(type => {
        const checkbox = document.createElement('div');
        checkbox.className = 'col-md-4 mb-2';
        checkbox.innerHTML = `
            <div class="form-check">
                <input class="form-check-input" type="checkbox" value="${type.id}" id="type${type.id}">
                <label class="form-check-label" for="type${type.id}">
                    <i class="fas ${type.icon}"></i> ${type.name}
                </label>
            </div>
        `;
        placeTypesCheckboxes.appendChild(checkbox);
    });

    // Add animation to form elements
    const formInputs = form.querySelectorAll('input, button, .form-check');
    formInputs.forEach((input, index) => {
        input.style.opacity = '0';
        input.style.transform = 'translateY(20px)';
        setTimeout(() => {
            input.style.transition = 'all 0.5s ease';
            input.style.opacity = '1';
            input.style.transform = 'translateY(0)';
        }, index * 100);
    });

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const budget = document.getElementById('budget').value;
        const duration = document.getElementById('duration').value;
        const selectedTypes = Array.from(document.querySelectorAll('input[type="checkbox"]:checked')).map(cb => parseInt(cb.value));

        if (selectedTypes.length === 0) {
            alert('Please select at least one place type.');
            return;
        }

        const data = {
            budget: parseInt(budget),
            duration: parseInt(duration),
            experience_types: selectedTypes
        };

        loadingIndicator.style.display = 'block';
        resultsDiv.style.display = 'none';

        try {
            console.log('Sending request with data:', data);
            const response = await fetch('http://127.0.0.1:4001/api/cities', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const cities = await response.json();
            console.log('Received cities:', cities);
            displayResults(cities);
        } catch (error) {
            console.error('Error:', error);
            resultsDiv.innerHTML = `<div class="alert alert-danger" role="alert">
                An error occurred: ${error.message}. Please try again.
            </div>`;
            resultsDiv.style.display = 'block';
        } finally {
            loadingIndicator.style.display = 'none';
        }
    });

    function displayResults(cities) {
        let resultHTML = '<h2 class="mb-4">Recommended Cities</h2>';
        if (cities.length === 0) {
            resultHTML += '<p>No cities match your criteria. Please try adjusting your preferences.</p>';
        } else {
            resultHTML += '<div class="row">';
            cities.forEach((city, index) => {
                resultHTML += `
                    <div class="col-md-4 mb-4">
                        <div class="card h-100">
                            <div class="card-body">
                                <h5 class="card-title">${city.name}</h5>
                                <p class="card-text">Match Score: ${city.match_score}%</p>
                                <p class="card-text">Matching Types:</p>
                                <ul>
                                    ${city.matching_types.map(type => `<li>${type}</li>`).join('')}
                                </ul>
                            </div>
                        </div>
                    </div>
                `;
            });
            resultHTML += '</div>';
        }
        resultsDiv.innerHTML = resultHTML;
        resultsDiv.style.display = 'block';
        
        // Animate results
        const cards = resultsDiv.querySelectorAll('.card');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            setTimeout(() => {
                card.style.transition = 'all 0.5s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100);
        });
    }
});

