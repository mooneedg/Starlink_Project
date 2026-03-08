import os
import pandas as pd
import json
import datetime
from datetime import timezone
from jinja2 import Environment, FileSystemLoader
import plotly.express as px
import webbrowser 
import pathlib     # NEW: Bulletproof cross-platform path handling


def generate_daily_report(runtime_seconds, failed_steps, data_fresh, db_path="database/SpaceData.db"):
   print("Generating Daily Conjunction Report...")
  
   events_path = "data/processed/conjunction_events.parquet"
   if os.path.exists(events_path):
       df_events = pd.read_parquet(events_path)
   else:
       df_events = pd.DataFrame(columns=['object_1', 'object_2', 'tca_timestamp', 'miss_distance_km', 'relative_velocity_kms', 'risk_score'])


   val_path = "data/processed/validation_metrics.json"
   if os.path.exists(val_path):
       with open(val_path, 'r') as f:
           val_metrics = json.load(f)
   else:
       val_metrics = {'recall': 'N/A', 'precision': 'N/A', 'mean_miss_distance_error_km': 'N/A'}


   total_objects = "Unknown"
   if os.path.exists(db_path):
       import sqlite3
       conn = sqlite3.connect(db_path)
       total_objects = pd.read_sql("SELECT COUNT(*) FROM space_objects", conn).iloc[0,0]
       conn.close()


   total_events = len(df_events)
   high_risk_events = len(df_events[df_events['risk_score'] >= 50]) if not df_events.empty else 0


   if not df_events.empty:
       top_10 = df_events.sort_values(by='risk_score', ascending=False).head(10).copy()
       top_10['miss_distance_km'] = top_10['miss_distance_km'].round(3)
       top_10['relative_velocity_kms'] = top_10['relative_velocity_kms'].round(2)
       top_10['risk_score'] = top_10['risk_score'].round(1)
       top_10_html = top_10[['object_1', 'object_2', 'tca_timestamp', 'miss_distance_km', 'relative_velocity_kms', 'risk_score']].to_html(index=False, classes='data-table', border=0)
   else:
       top_10_html = "<p>No conjunction events detected today.</p>"


   if not df_events.empty:
       fig = px.histogram(df_events, x="risk_score", nbins=50, title="Risk Score Distribution", color_discrete_sequence=['#00E5FF'])
       fig.update_layout(paper_bgcolor='#12161F', plot_bgcolor='#12161F', font=dict(color='#E2E8F0'), margin=dict(t=40, b=10, l=10, r=10))
       risk_chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
   else:
       risk_chart_html = "<p>No data for chart.</p>"


   env = Environment(loader=FileSystemLoader('reporting/templates'))
   template = env.get_template('daily_report.html')


   now_utc = datetime.datetime.now(timezone.utc)
   date_str = now_utc.strftime('%Y-%m-%d %H:%M:%S')
   file_date_str = now_utc.strftime('%Y%m%d')


   html_out = template.render(
       date=date_str,
       total_objects=total_objects,
       total_events=total_events,
       high_risk_events=high_risk_events,
       top_events_table=top_10_html,
       recall=f"{val_metrics.get('recall', 0)*100:.1f}%" if isinstance(val_metrics.get('recall'), float) else 'N/A',
       precision=f"{val_metrics.get('precision', 0)*100:.1f}%" if isinstance(val_metrics.get('precision'), float) else 'N/A',
       mean_miss_error=round(val_metrics.get('mean_miss_distance_error_km', 0), 3) if isinstance(val_metrics.get('mean_miss_distance_error_km'), float) else 'N/A',
       risk_chart_html=risk_chart_html,
       runtime_seconds=round(runtime_seconds, 1),
       failed_steps="None" if not failed_steps else ", ".join(failed_steps),
       data_fresh=data_fresh
   )


   os.makedirs('reports', exist_ok=True)
   report_path = f"reports/daily_report_{file_date_str}.html"
   with open(report_path, 'w') as f:
       f.write(html_out)
      
   # === THE CROSS-PLATFORM LINK FIX ===
   # 1. Use pathlib to generate the mathematically correct URI for Mac/Windows
   abs_path_obj = pathlib.Path(report_path).resolve()
   file_uri = abs_path_obj.as_uri()
  
   # 2. Use ANSI escape codes (OSC 8) to force modern terminals to make it clickable
   clickable_link = f"\033]8;;{file_uri}\033\\{abs_path_obj.name}\033]8;;\033\\"
  
   print(f"Terminal Link: {clickable_link}")
  
   # 3. Safely command the OS to open the file in the default browser
   try:
       webbrowser.open(file_uri)
   except Exception as e:
       print(f"⚠️ Could not auto-open browser: {e}")


   # === HISTORICAL METRICS ===
   history_path = "data/processed/metrics_history.parquet"
   new_record = pd.DataFrame([{
       'date': date_str,
       'total_events': total_events,
       'recall': val_metrics.get('recall', None),
       'precision': val_metrics.get('precision', None),
       'avg_miss_distance': df_events['miss_distance_km'].mean() if not df_events.empty else None,
       'avg_runtime_seconds': runtime_seconds
   }])


   if os.path.exists(history_path):
       history_df = pd.read_parquet(history_path)
       history_df = pd.concat([history_df, new_record], ignore_index=True)
   else:
       history_df = new_record
      
   history_df.to_parquet(history_path, index=False)
   print("Historical metrics updated.")