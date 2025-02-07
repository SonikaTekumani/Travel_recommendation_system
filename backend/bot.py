from flask import Flask, request, jsonify
import pandas as pd
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)  # Allow requests from your frontend

# Load datasets
try:
    states_df = pd.read_csv(r'C:\Users\hp\OneDrive\Desktop\sonikapy\travel_bot\backend\states_and_union_territories.csv')
    cities_df = pd.read_csv(r'C:\Users\hp\OneDrive\Desktop\sonikapy\travel_bot\backend\cities.csv')
    budget_duration_df = pd.read_csv(r'C:\Users\hp\OneDrive\Desktop\sonikapy\travel_bot\backend\city_budget_duration.csv')
    cities_type_df = pd.read_csv(r'C:\Users\hp\OneDrive\Desktop\sonikapy\travel_bot\backend\cities_type_data.csv')
except FileNotFoundError as e:
    print(f"Error: {e.filename} not found. Please ensure all required datasets are in the 'datasets' folder.")
    exit(1)
except pd.errors.EmptyDataError:
    print(f"Error: One of the CSV files is empty. Please check the contents of your dataset files.")
    exit(1)
except Exception as e:
    print(f"An unexpected error occurred while loading datasets: {e}")
    exit(1)

@app.route('/api/cities', methods=['POST'])
def get_cities():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200  # Respond to preflight request
    
    try:
        data = request.json
        budget = data['budget']
        duration = data['duration']
        experience_types = data['experience_types']
        if not isinstance(budget, (int, float)) or not isinstance(duration, (int, float)):
            return jsonify({"error": "Budget and duration must be numbers."}), 400
        
        budget_duration_df['Duration_Range'] = budget_duration_df['Duration_Range'].str.replace(r'[^\d\-]', '', regex=True)

        # Filter cities based on budget and duration
        filtered_cities = budget_duration_df[
            (budget_duration_df['Budget_Range'].str.split('-').str[0].astype(int) <= budget) &
            (budget_duration_df['Budget_Range'].str.split('-').str[1].astype(int) >= budget) &
            (budget_duration_df['Duration_Range'].str.split('-').str[0].astype(int) <= duration) &
            (budget_duration_df['Duration_Range'].str.split('-').str[1].astype(int) >= duration)
        ]

        # Get cities that match experience types
        city_matches = cities_type_df[cities_type_df['Type_ID'].isin(experience_types)].groupby('City_ID').agg({
            'Type_ID': list,
            'City_Name': 'first'
        }).reset_index()
        
        # Filter cities based on experience types
        final_cities = filtered_cities[filtered_cities['City_ID'].isin(city_matches['City_ID'])]

        # Merge to get matching types for each city
        final_cities = final_cities.merge(city_matches[['City_ID', 'Type_ID']], on='City_ID', how='left')

        # Calculate match score (percentage of requested types that are present)
        final_cities['match_score'] = final_cities['Type_ID'].apply(lambda x: len(set(x) & set(experience_types)) / len(experience_types) * 100)

        # Sort by match score
        final_cities = final_cities.sort_values('match_score', ascending=False)

        # Get type names for matching types
        type_names = cities_type_df[['Type_ID', 'Type_Name']].drop_duplicates().set_index('Type_ID')['Type_Name'].to_dict()

        # Prepare result
        result = final_cities.apply(lambda row: {
            'name': row['City_Name'],
            'match_score': round(row['match_score'], 2),
            'matching_types': [type_names[type_id] for type_id in set(row['Type_ID']) & set(experience_types)]
        }, axis=1).tolist()

        return jsonify(result)
    except KeyError as e:
        print(f"Error: Missing key '{e.args[0]}' in request JSON.")
        return jsonify({"error": f"Missing key '{e.args[0]}' in request JSON."}), 400
    except Exception as e:
        print(f"Error: {e}")  # Log the error to the console
        return jsonify({"error": str(e)}), 500  # Return a 500 error with the message

if __name__ == '__main__':
    app.run(debug=True, port=4001)