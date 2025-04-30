from flask import Flask, render_template, request, jsonify
import pandas as pd
from datetime import datetime

app = Flask(__name__)

def load_data():
    try:
        # Load CSV data
        df = pd.read_csv('hasan.csv')
        
        # Convert date column to datetime and calculate week numbers
        df['onboard_date_v2'] = pd.to_datetime(df['onboard_date_v2'],dayfirst=True,errors='coerce')
        df['week'] = df['onboard_date_v2'].dt.isocalendar().week
        df['year'] = df['onboard_date_v2'].dt.isocalendar().year
        
        # Ensure numeric columns are properly formatted
        numeric_cols = [
            'sla_end_to_end_exclude_weekend1',
            'wo_adv_std_exclude_weekend',
            'complaince_activation_exclude_weekend',
            'xws_activation_to_idv',
            'xws_idv_to_system_activation'
        ]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df.dropna(subset=['supplier_name'])
        
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def get_week_info():
    today = datetime.now()
    current_week = today.isocalendar().week
    current_year = today.isocalendar().year
    previous_week = current_week - 1 if current_week > 1 else 52
    previous_year = current_year if current_week > 1 else current_year - 1
    
    return {
        'current_week': current_week,
        'current_year': current_year,
        'previous_week': previous_week,
        'previous_year': previous_year
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_suppliers')
def get_suppliers():
    df = load_data()
    suppliers = df['supplier_name'].unique().tolist()
    return jsonify(suppliers)

@app.route('/get_overall_metrics')
def get_overall_metrics():
    try:
        df = load_data()
        week_info = get_week_info()
        
        # Current week data
        current_data = df[
            (df['week'] == week_info['current_week']) &
            (df['year'] == week_info['current_year'])
        ]
        
        # Previous week data
        previous_data = df[
            (df['week'] == week_info['previous_week']) &
            (df['year'] == week_info['previous_year'])
        ]
        
        if current_data.empty or previous_data.empty:
            return jsonify({'error': 'Not enough data to compare'}), 404
        
        # Calculate metrics
        current_metrics = {
            'overall_tat': current_data['sla_end_to_end_exclude_weekend1'].mean(),
            'xws_activation': current_data['wo_adv_std_exclude_weekend'].mean(),
            'system_activation': current_data['complaince_activation_exclude_weekend'].mean(),
            'xws_to_idv': current_data['xws_activation_to_idv'].mean(),
            'idv_to_system': current_data['xws_idv_to_system_activation'].mean()
        }
        
        previous_metrics = {
            'overall_tat': previous_data['sla_end_to_end_exclude_weekend1'].mean(),
            'xws_activation': previous_data['wo_adv_std_exclude_weekend'].mean(),
            'system_activation': previous_data['complaince_activation_exclude_weekend'].mean(),
            'xws_to_idv': previous_data['xws_activation_to_idv'].mean(),
            'idv_to_system': previous_data['xws_idv_to_system_activation'].mean()
        }
        
        # Calculate differences
        differences = {
            'overall_tat': current_metrics['overall_tat'] - previous_metrics['overall_tat'],
            'xws_activation': current_metrics['xws_activation'] - previous_metrics['xws_activation'],
            'system_activation': current_metrics['system_activation'] - previous_metrics['system_activation'],
            'xws_to_idv': current_metrics['xws_to_idv'] - previous_metrics['xws_to_idv'],
            'idv_to_system': current_metrics['idv_to_system'] - previous_metrics['idv_to_system']
        }
        
        return jsonify({
            'differences': differences,
            'current_metrics': current_metrics,
            'previous_metrics': previous_metrics
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_all_suppliers_data')
def get_all_suppliers_data():
    try:
        df = load_data()
        week_info = get_week_info()
        
        all_data = []
        suppliers = df['supplier_name'].unique()
        
        for supplier in suppliers:
            current_data = df[
                (df['supplier_name'] == supplier) &
                (df['week'] == week_info['current_week']) &
                (df['year'] == week_info['current_year'])
            ]
            
            previous_data = df[
                (df['supplier_name'] == supplier) &
                (df['week'] == week_info['previous_week']) &
                (df['year'] == week_info['previous_year'])
            ]
            
            if not current_data.empty:
                # Current week metrics
                current_metrics = {
                    'supplier': supplier,
                    'total_onboarding': current_data['cw_num'].nunique(),
                    'current_overall_tat': current_data['sla_end_to_end_exclude_weekend1'].mean(),
                    'current_xws_activation': current_data['wo_adv_std_exclude_weekend'].mean(),
                    'current_system_activation': current_data['complaince_activation_exclude_weekend'].mean(),
                    'current_xws_to_idv': current_data['xws_activation_to_idv'].mean(),
                    'current_idv_to_system': current_data['xws_idv_to_system_activation'].mean()
                }
                
                # Previous week metrics
                previous_metrics = {
                    'previous_overall_tat': previous_data['sla_end_to_end_exclude_weekend1'].mean() if not previous_data.empty else None,
                    'previous_xws_activation': previous_data['wo_adv_std_exclude_weekend'].mean() if not previous_data.empty else None,
                    'previous_system_activation': previous_data['complaince_activation_exclude_weekend'].mean() if not previous_data.empty else None,
                    'previous_xws_to_idv': previous_data['xws_activation_to_idv'].mean() if not previous_data.empty else None,
                    'previous_idv_to_system': previous_data['xws_idv_to_system_activation'].mean() if not previous_data.empty else None
                }
                
                # Calculate differences (current week - previous week)
                differences = {
                    'supplier': supplier,
                    'total_onboarding': current_metrics['total_onboarding'],
                    'overall_tat_diff': current_metrics['current_overall_tat'] - previous_metrics['previous_overall_tat'] if previous_metrics['previous_overall_tat'] is not None else None,
                    'xws_activation_diff': current_metrics['current_xws_activation'] - previous_metrics['previous_xws_activation'] if previous_metrics['previous_xws_activation'] is not None else None,
                    'system_activation_diff': current_metrics['current_system_activation'] - previous_metrics['previous_system_activation'] if previous_metrics['previous_system_activation'] is not None else None,
                    'xws_to_idv_diff': current_metrics['current_xws_to_idv'] - previous_metrics['previous_xws_to_idv'] if previous_metrics['previous_xws_to_idv'] is not None else None,
                    'idv_to_system_diff': current_metrics['current_idv_to_system'] - previous_metrics['previous_idv_to_system'] if previous_metrics['previous_idv_to_system'] is not None else None,
                    # Include current and previous values
                    'current_overall_tat': current_metrics['current_overall_tat'],
                    'previous_overall_tat': previous_metrics['previous_overall_tat'],
                    'current_xws_activation': current_metrics['current_xws_activation'],
                    'previous_xws_activation': previous_metrics['previous_xws_activation'],
                    'current_system_activation': current_metrics['current_system_activation'],
                    'previous_system_activation': previous_metrics['previous_system_activation'],
                    'current_xws_to_idv': current_metrics['current_xws_to_idv'],
                    'previous_xws_to_idv': previous_metrics['previous_xws_to_idv'],
                    'current_idv_to_system': current_metrics['current_idv_to_system'],
                    'previous_idv_to_system': previous_metrics['previous_idv_to_system']
                }
                
                all_data.append(differences)
        
        # Sort by total onboarding (highest first)
        all_data.sort(key=lambda x: x['total_onboarding'], reverse=True)
        
        return jsonify(all_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
