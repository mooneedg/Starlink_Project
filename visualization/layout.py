from dash import dcc, html


def create_layout(all_norad_ids, min_date, max_date, metadata):
   dropdown_options = [
       {'label': f"{metadata.get(str(nid), {}).get('name', str(nid))} ({nid})", 'value': str(nid)}
       for nid in all_norad_ids
   ]
  
   colors = {
       'bg_app': '#090B10',      
       'bg_panel': '#12161F',    
       'border': '#222631',      
       'text_main': '#E2E8F0',   
       'text_muted': '#94A3B8',  
       'accent': '#00E5FF',      
       'input_bg': '#1A1E29'     
   }


   section_title_style = {'color': colors['text_muted'], 'fontSize': '11px', 'fontWeight': '700', 'textTransform': 'uppercase', 'letterSpacing': '1px', 'marginBottom': '10px', 'marginTop': '25px'}
   label_style = {'color': colors['text_main'], 'fontSize': '13px', 'marginBottom': '5px', 'display': 'block'}
   input_style = {'backgroundColor': colors['input_bg'], 'color': 'white', 'border': f"1px solid {colors['border']}", 'borderRadius': '4px', 'padding': '6px 10px', 'width': '100%', 'boxSizing': 'border-box', 'fontSize': '13px'}
   radio_style = {'display': 'flex', 'flexDirection': 'column', 'gap': '8px', 'fontSize': '13px'}


   return html.Div(
       style={
           # UI FIX: Absolute positioning forces the Div to fill the screen, bypassing the browser's default body margin
           'position': 'absolute', 'top': '0', 'left': '0', 'right': '0', 'bottom': '0',
           'display': 'flex', 'backgroundColor': colors['bg_app'],
           'fontFamily': 'system-ui, -apple-system, sans-serif',
           'overflow': 'hidden' # Locks the master window from scrolling
       },
       children=[


           # === LEFT SIDEBAR (Controls & Filters) ===
           html.Div(
               id='sidebar-container',
               style={'width': '340px', 'minWidth': '340px', 'backgroundColor': colors['bg_panel'], 'borderRight': f"1px solid {colors['border']}", 'display': 'flex', 'flexDirection': 'column', 'boxShadow': '2px 0 10px rgba(0,0,0,0.3)', 'zIndex': '10'},
               children=[
                   html.Div(
                       style={'padding': '20px', 'borderBottom': f"1px solid {colors['border']}", 'backgroundColor': '#0D1017'},
                       children=[
                           html.H2("STARLINK", style={'margin': '0', 'color': colors['text_main'], 'fontSize': '22px', 'fontWeight': '800', 'letterSpacing': '1px'}),
                           html.Div("COLLISION AVOIDANCE SYSTEM", style={'color': colors['accent'], 'fontSize': '10px', 'fontWeight': '700', 'letterSpacing': '1.5px', 'marginTop': '4px'})
                       ]
                   ),
                   html.Div(
                       style={'flex': '1', 'overflowY': 'auto', 'padding': '0 20px 20px 20px'},
                       children=[
                           html.Div(style=section_title_style, children="Manual Targeting"),
                           html.Label("Search Satellite Catalog:", style=label_style),
                           dcc.Dropdown(
                               id='sat-dropdown', options=dropdown_options, multi=True, placeholder="Search NORAD ID or Name...",
                               style={'color': 'black', 'fontSize': '13px'}
                           ),
                           html.Button("Return to Earth View", id='reset-btn', n_clicks=0,
                               style={
                                   'width': '100%', 'marginTop': '10px', 'padding': '10px',
                                   'backgroundColor': colors['accent'], 'color': 'black',
                                   'border': 'none', 'borderRadius': '4px',
                                   'cursor': 'pointer', 'fontSize': '13px', 'fontWeight': 'bold',
                                   'boxShadow': '0 0 10px rgba(0, 229, 255, 0.2)'
                               }
                           ),
                           html.Div(style=section_title_style, children="Event Filters"),
                           html.Label("Filter Object Groups:", style=label_style),
                           dcc.Checklist(
                               id='group-checklist',
                               options=[
                                   {'label': html.Span(' Starlink', style={'color': '#00FFFF', 'fontWeight': '500'}), 'value': 'Starlink'},
                                   {'label': html.Span(' Spacecraft', style={'color': '#00FF00', 'fontWeight': '500'}), 'value': 'Spacecraft'},
                                   {'label': html.Span(' Debris / Other', style={'color': '#FFA500', 'fontWeight': '500'}), 'value': 'Debris/Other'}
                               ],
                               value=['Starlink', 'Spacecraft', 'Debris/Other'],
                               style=radio_style, inputStyle={'marginRight': '8px', 'cursor': 'pointer'}
                           ),


                           html.Label("Min Miss Distance (km):", style={**label_style, 'marginTop': '15px'}),
                           dcc.Input(id='min-dist-filter', type='number', value=0.1, min=0.0, step=0.1, style=input_style),


                           html.Label("Event Modifiers:", style={**label_style, 'marginTop': '15px'}),
                           dcc.Checklist(
                               id='starlink-focus-filter', options=[{'label': html.Span(' Must Involve Starlink', style={'color': 'white'}), 'value': 'focus'}],
                               value=['focus'], style=radio_style, inputStyle={'marginRight': '8px', 'cursor': 'pointer'}
                           ),
                           dcc.Checklist(
                               id='ghost-filter', options=[{'label': html.Span(' Hide Database Ghosts', style={'color': 'white'}), 'value': 'hide'}],
                               value=['hide'], style={**radio_style, 'marginTop': '8px'}, inputStyle={'marginRight': '8px', 'cursor': 'pointer'}
                           ),
                           dcc.Checklist(
                               id='unique-event-filter', options=[{'label': html.Span(' Max 1 Event / Object', style={'color': 'white'}), 'value': 'unique'}],
                               value=[], style={**radio_style, 'marginTop': '8px'}, inputStyle={'marginRight': '8px', 'cursor': 'pointer'}
                           ),


                           html.Div(style=section_title_style, children="Risk & Timeline"),
                           html.Label("Show Top N Events:", style=label_style),
                           html.Div(style={'padding': '0 10px', 'marginBottom': '15px'}, children=[
                               dcc.Slider(
                                   id='risk-slider', min=1, max=100, step=1, value=20,
                                   marks={1: {'label': '1', 'style': {'color': colors['text_muted']}}, 50: {'label': '50', 'style': {'color': colors['text_muted']}}, 100: {'label': '100', 'style': {'color': colors['text_muted']}}}
                               )
                           ]),


                           html.Label("TCA Time Window:", style=label_style),
                           html.Div(
                               style={'color': 'black'},
                               children=[
                                   dcc.DatePickerRange(
                                       id='date-picker', min_date_allowed=min_date, max_date_allowed=max_date,
                                       start_date=min_date, end_date=max_date, display_format='YYYY-MM-DD',
                                       style={'width': '100%'}
                                   )
                               ]
                           ),


                           html.Div(style=section_title_style, children="Render Settings"),
                           html.Label("Orbit Track Length (± mins):", style=label_style),
                           html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '10px'}, children=[
                               dcc.Input(id='track-length-input', type='number', value=30, min=0, step=10, style={**input_style, 'width': '80px', 'marginTop': '0'}),
                               html.Span("(0 = Dots Only)", style={'color': colors['text_muted'], 'fontSize': '11px'})
                           ]),


                           html.Label("Targeted Orbit Lines:", style={**label_style, 'marginTop': '15px'}),
                           dcc.RadioItems(
                               id='targeting-radio', options=[{'label': ' Highest Risk Event', 'value': 'single'}, {'label': ' Top N Events', 'value': 'multi'}],
                               value='multi', style=radio_style, inputStyle={'marginRight': '8px'}, labelStyle={'color': 'white'}
                           ),


                           html.Label("Background Swarm:", style={**label_style, 'marginTop': '15px'}),
                           dcc.RadioItems(
                               id='swarm-radio', options=[{'label': ' Hidden', 'value': 'off'}, {'label': ' Show All Catalog', 'value': 'on'}],
                               value='off', style=radio_style, inputStyle={'marginRight': '8px'}, labelStyle={'color': 'white'}
                           ),


                           html.Label("Camera Mode:", style={**label_style, 'marginTop': '15px'}),
                           dcc.RadioItems(
                               id='drag-mode', options=[{'label': ' Rotate', 'value': 'orbit'}, {'label': ' Pan', 'value': 'pan'}],
                               value='orbit', style=radio_style, inputStyle={'marginRight': '8px'}, labelStyle={'color': 'white'}
                           ),
                           dcc.RadioItems(
                               id='zoom-lock', options=[{'label': ' Auto-Fit Bounds', 'value': 'auto'}, {'label': ' Lock to LEO', 'value': 'leo'}],
                               value='leo', style={**radio_style, 'marginTop': '8px'}, inputStyle={'marginRight': '8px'}, labelStyle={'color': 'white'}
                           ),
                           html.Div(style={'height': '30px'})
                       ]
                   )
               ]
           ),


           # === RIGHT MAIN AREA (Visualizations) ===
           html.Div(
               style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'position': 'relative', 'minWidth': '0'},
               children=[
                  
                   # --- TOP ACTION BAR WITH BRANDING ---
                   html.Div(
                       style={'height': '40px', 'backgroundColor': '#0D1017', 'borderBottom': f"1px solid {colors['border']}", 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'padding': '0 20px'},
                       children=[
                           html.Button("☰ Toggle Filters", id='toggle-sidebar-btn', n_clicks=0, style={'backgroundColor': 'transparent', 'color': colors['text_main'], 'border': '1px solid #333', 'borderRadius': '4px', 'padding': '4px 10px', 'cursor': 'pointer', 'fontWeight': 'bold', 'fontSize': '12px'}),
                          
                           # BRANDING MESSAGE: Perfectly centered and customizable!
                           html.Div(
                               "Developed by Edgar Moonemalle | Data Source: CelesTrak & Space-Track.org",
                               style={'color': colors['text_muted'], 'fontSize': '12px', 'letterSpacing': '0.5px'}
                           ),


                           html.Button("Toggle Telemetry", id='toggle-telemetry-btn', n_clicks=0, style={'backgroundColor': 'transparent', 'color': colors['accent'], 'border': '1px solid #00E5FF', 'borderRadius': '4px', 'padding': '4px 10px', 'cursor': 'pointer', 'fontWeight': 'bold', 'fontSize': '12px'})
                       ]
                   ),


                   html.Div(
                       style={'flex': '6', 'position': 'relative', 'backgroundColor': '#000', 'minHeight': '0'},
                       children=[
                           dcc.Graph(id='orbit-graph', style={'height': '100%', 'width': '100%'}, config={'scrollZoom': True, 'displayModeBar': False})
                       ]
                   ),


                   html.Div(
                       id='telemetry-container',
                       style={'flex': '4', 'minHeight': '0', 'display': 'flex', 'flexDirection': 'column', 'borderTop': f"2px solid {colors['accent']}", 'backgroundColor': colors['bg_panel']},
                       children=[
                           html.Div(
                               style={'height': '45px', 'backgroundColor': '#0D1017', 'display': 'flex', 'alignItems': 'center', 'padding': '0 20px'},
                               children=[
                                   html.Div("TELEMETRY VIEW", style={'color': colors['accent'], 'fontSize': '12px', 'fontWeight': '700', 'letterSpacing': '1px', 'marginRight': '20px'}),
                                   dcc.Dropdown(
                                       id='telemetry-dropdown', options=[], placeholder="Select an event to load telemetry...",
                                       style={'color': 'black', 'width': '600px', 'fontSize': '13px'}
                                   )
                               ]
                           ),
                           dcc.Graph(id='telemetry-graph', style={'flex': '1', 'width': '100%'}, config={'displayModeBar': False})
                       ]
                   )
               ]
           )
       ]
   )