import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import DeliveryOutlook from './DeliveryOutlook';
import { api } from './api';
import { downloadCaptured } from './CommandRouteReview';
import type { Network } from './types';

vi.mock('./api', () => ({ api: vi.fn() }));
vi.mock('./CommandRouteReview', () => ({ downloadCaptured: vi.fn() }));

// These transport fixtures were captured from build_delivery_outlook with the
// actual allocation and thermal helpers over the seven-candidate unit-test
// simulation below. They are neither operator observations nor claimed forecasts.
// Only the retrieval timestamp is fixed for the UI tests. No providers are called.
const captured = {"network":{"seed":20261026,"provenance":"Explicit UI unit-test simulation; not operator data","nodes":[{"id":"DC1","name":"Columbia DC (simulated)","kind":"dc","coordinates":[-92.3341,38.9517],"capacity_kg":12000},{"id":"SUP1","name":"Columbia supplier (simulated)","kind":"supplier","coordinates":[-92.4141,39.011700000000005],"capacity_kg":6000},{"id":"D01","name":"Simulated test destination D01","kind":"destination","coordinates":[-92.42686574587837,38.90267193182352],"demand_kg":500},{"id":"D02","name":"Simulated test destination D02","kind":"destination","coordinates":[-94.66668154137945,39.09718904789093],"demand_kg":500},{"id":"D03","name":"Simulated test destination D03","kind":"destination","coordinates":[-92.16343117674066,38.488262137080646],"demand_kg":500},{"id":"D04","name":"Simulated test destination D04","kind":"destination","coordinates":[-93.31616801496607,37.18283988350218],"demand_kg":500},{"id":"D05","name":"Simulated test destination D05","kind":"destination","coordinates":[-90.23742422131505,38.653449031901474],"demand_kg":500},{"id":"D06","name":"Simulated test destination D06","kind":"destination","coordinates":[-92.38904895518336,38.95136030760434],"demand_kg":500},{"id":"D07","name":"Simulated test destination D07","kind":"destination","coordinates":[-94.61661228995621,39.16906599628995],"demand_kg":500}],"trucks":[{"id":"T01","capacity_kg":1800,"refrigerated":true,"eligible":true},{"id":"T02","capacity_kg":1800,"refrigerated":true,"eligible":true}],"lots":[{"id":"L01","supplier_id":"SUP1","inventory_kg":3000,"held":true,"recalled":false,"eligible":true,"shelf_life_hours":72},{"id":"L02","supplier_id":"SUP1","inventory_kg":3000,"held":false,"recalled":false,"eligible":true,"shelf_life_hours":72}],"shipments":[{"id":"SH01","origin":"DC1","destination":"D01","lot_id":"L01","truck_id":"T01","quantity_kg":400,"deadline_hours":6,"estimated_hours":1.5,"estimated_distance_km":120,"routing_provenance":"haversine x 1.25 at 65 km/h; not road geometry","temperature_c":1.2,"review_priority":"routine","status":"pending dispatcher approval"},{"id":"SH02","origin":"DC1","destination":"D02","lot_id":"L02","truck_id":"T02","quantity_kg":400,"deadline_hours":6,"estimated_hours":2,"estimated_distance_km":120,"routing_provenance":"haversine x 1.25 at 65 km/h; not road geometry","temperature_c":8.5,"review_priority":"high","status":"pending dispatcher approval"},{"id":"SH03","origin":"DC1","destination":"D03","lot_id":"L02","truck_id":"T01","quantity_kg":400,"deadline_hours":6,"estimated_hours":5.5,"estimated_distance_km":120,"routing_provenance":"haversine x 1.25 at 65 km/h; not road geometry","temperature_c":1.2,"review_priority":"routine","status":"pending dispatcher approval"},{"id":"SH04","origin":"DC1","destination":"D04","lot_id":"L02","truck_id":"T02","quantity_kg":400,"deadline_hours":6,"estimated_hours":5.5,"estimated_distance_km":120,"routing_provenance":"haversine x 1.25 at 65 km/h; not road geometry","temperature_c":1.2,"review_priority":"routine","status":"pending dispatcher approval"},{"id":"SH05","origin":"DC1","destination":"D05","lot_id":"L02","truck_id":"T01","quantity_kg":400,"deadline_hours":6,"estimated_hours":5.5,"estimated_distance_km":120,"routing_provenance":"haversine x 1.25 at 65 km/h; not road geometry","temperature_c":1.2,"review_priority":"routine","status":"pending dispatcher approval"},{"id":"SH06","origin":"DC1","destination":"D06","lot_id":"L02","truck_id":"T02","quantity_kg":400,"deadline_hours":6,"estimated_hours":5.5,"estimated_distance_km":120,"routing_provenance":"haversine x 1.25 at 65 km/h; not road geometry","temperature_c":1.2,"review_priority":"routine","status":"pending dispatcher approval"},{"id":"SH07","origin":"DC1","destination":"D07","lot_id":"L02","truck_id":"T01","quantity_kg":400,"deadline_hours":6,"estimated_hours":5.5,"estimated_distance_km":120,"routing_provenance":"haversine x 1.25 at 65 km/h; not road geometry","temperature_c":1.2,"review_priority":"routine","status":"pending dispatcher approval"}],"telemetry":[],"events":[],"revision":3},"baseline":{"kind":"delivery_outlook","snapshot_id":"d0a6792f9bebe352dce3acc374c1f7d3d35040b6bf1a3b28d03f4d233de4c808","network_snapshot_id":"76c41cb5ce8a19112eee88a6d04bb17381e93e902946029312ec8f1d90eeb948","network_revision":3,"generated_at":"2026-10-29T18:00:00+00:00","read_only":true,"simulation":true,"operational_state_modified":false,"planning_horizon_hours":6,"parameters":{"added_delay_minutes":0,"ambient_temperature_c":30.0,"fault_truck_id":null},"provenance":{"model_kind":"deterministic planning projection","network_input":"simulated network and fixed candidate trips; not real supply contracts","weather_input":"user planning assumption; not an observed weather value or fetched forecast","cargo_input":"simulated current cargo temperature; not physical sensor telemetry","travel_input":"fixed origin-destination planning duration, including already recorded simulated delays; no new road routing","model_performance":"No prospective delay or cargo-failure skill is established here. Saved FSIS sampling model evaluation remains a separate scientific task."},"baseline":{"scenario":"A","name":"Baseline distribution","total_logistics_cost":1308,"unmet_demand_kg":1100,"selected_shipments":6,"supplied_kg":2400,"affected_shipments":1,"review_priority_count":1,"food_waste_kg":0,"solver_status":"OPTIMAL","feasible":true,"constraint_violations":0,"constraint_review_passed":true,"proposed_hold_lots":[],"selected_ids":["SH02","SH03","SH04","SH05","SH06","SH07"],"selected_lots":{"SH02":"L02","SH03":"L02","SH04":"L02","SH05":"L02","SH06":"L02","SH07":"L02"},"requires_human_approval":true},"scenarios":[{"scenario":"A","name":"Baseline distribution","summary":{"scenario":"A","name":"Baseline distribution","total_logistics_cost":1308,"unmet_demand_kg":1100,"selected_shipments":6,"supplied_kg":2400,"affected_shipments":1,"review_priority_count":1,"food_waste_kg":0,"solver_status":"OPTIMAL","feasible":true,"constraint_violations":0,"constraint_review_passed":true,"proposed_hold_lots":[],"selected_ids":["SH02","SH03","SH04","SH05","SH06","SH07"],"selected_lots":{"SH02":"L02","SH03":"L02","SH04":"L02","SH05":"L02","SH06":"L02","SH07":"L02"},"requires_human_approval":true},"delta_vs_baseline":{"total_logistics_cost":0,"unmet_demand_kg":0,"selected_shipments":0,"supplied_kg":0,"affected_shipments":0,"review_priority_count":0,"food_waste_kg":0}},{"scenario":"B","name":"Targeted verification","summary":{"scenario":"B","name":"Targeted verification","total_logistics_cost":1383,"unmet_demand_kg":1100,"selected_shipments":6,"supplied_kg":2400,"affected_shipments":1,"review_priority_count":1,"food_waste_kg":0,"solver_status":"OPTIMAL","feasible":true,"constraint_violations":0,"constraint_review_passed":true,"proposed_hold_lots":[],"selected_ids":["SH02","SH03","SH04","SH05","SH06","SH07"],"selected_lots":{"SH02":"L02","SH03":"L02","SH04":"L02","SH05":"L02","SH06":"L02","SH07":"L02"},"requires_human_approval":true},"delta_vs_baseline":{"total_logistics_cost":75,"unmet_demand_kg":0,"selected_shipments":0,"supplied_kg":0,"affected_shipments":0,"review_priority_count":0,"food_waste_kg":0}},{"scenario":"C","name":"Precautionary hold pending review","summary":{"scenario":"C","name":"Precautionary hold pending review","total_logistics_cost":0,"unmet_demand_kg":3500,"selected_shipments":0,"supplied_kg":0,"affected_shipments":7,"review_priority_count":0,"food_waste_kg":0,"solver_status":"OPTIMAL","feasible":true,"constraint_violations":0,"constraint_review_passed":true,"proposed_hold_lots":["L02"],"selected_ids":[],"selected_lots":{},"requires_human_approval":true},"delta_vs_baseline":{"total_logistics_cost":-1308,"unmet_demand_kg":2400,"selected_shipments":-6,"supplied_kg":-2400,"affected_shipments":6,"review_priority_count":-1,"food_waste_kg":0}},{"scenario":"D","name":"Alternative eligible supply","summary":{"scenario":"D","name":"Alternative eligible supply","total_logistics_cost":1571,"unmet_demand_kg":700,"selected_shipments":7,"supplied_kg":2800,"affected_shipments":0,"review_priority_count":1,"food_waste_kg":0,"solver_status":"OPTIMAL","feasible":true,"constraint_violations":0,"constraint_review_passed":true,"proposed_hold_lots":[],"selected_ids":["SH01","SH02","SH03","SH04","SH05","SH06","SH07"],"selected_lots":{"SH01":"L02","SH02":"L02","SH03":"L02","SH04":"L02","SH05":"L02","SH06":"L02","SH07":"L02"},"requires_human_approval":true},"delta_vs_baseline":{"total_logistics_cost":263,"unmet_demand_kg":-400,"selected_shipments":1,"supplied_kg":400,"affected_shipments":-1,"review_priority_count":0,"food_waste_kg":0}}],"summary":{"total_demand_kg":3500,"before_unmet_demand_kg":1100,"after_unmet_demand_kg":1100,"unmet_demand_change_kg":0,"selected_shipments_before":6,"selected_shipments_after":6,"candidate_deadline_misses":0,"candidate_temperature_reviews":1,"candidate_shipments":7},"shipments":[{"id":"SH01","truck_id":"T01","lot_id":"L01","destination_id":"D01","destination_name":"Simulated test destination D01","quantity_kg":400,"duration_before_hours":1.5,"duration_after_hours":1.5,"deadline_hours":6,"deadline_margin_hours":4.5,"misses_deadline":false,"selected_in_baseline":false,"selected_after_A":false,"exclusion_reasons":["lot held"],"temperature":{"checked_hours":1.5,"checkpoint":"at_modeled_arrival","projected_temperature_c":1.991,"max_temperature_c":1.991,"time_above_threshold_minutes":0,"review_required":false,"refrigeration_fault":false,"thermal_control_unavailable":false,"fault_source":"normal refrigeration assumption","initial_temperature_c":1.2,"provenance":"simulated cargo-temperature scenario projection; not observed sensor data or a validated failure-risk model","assumptions":["First-order thermal response; fault time constant 120 minutes, normal control 20 minutes","Normal assumed control equilibrium 2°C, with a small uncalibrated ambient penalty above 30°C","4°C is a conservative demonstration review threshold, not a lot disposition rule","Bands are parameter-sensitivity ranges, not statistical confidence intervals","No pathogen growth, consumer illness probability or automatic hold decision"]}},{"id":"SH02","truck_id":"T02","lot_id":"L02","destination_id":"D02","destination_name":"Simulated test destination D02","quantity_kg":400,"duration_before_hours":2,"duration_after_hours":2.0,"deadline_hours":6,"deadline_margin_hours":4.0,"misses_deadline":false,"selected_in_baseline":true,"selected_after_A":true,"exclusion_reasons":[],"temperature":{"checked_hours":2.0,"checkpoint":"at_modeled_arrival","projected_temperature_c":2.016,"max_temperature_c":8.5,"time_above_threshold_minutes":23.57,"review_required":true,"refrigeration_fault":false,"thermal_control_unavailable":false,"fault_source":"normal refrigeration assumption","initial_temperature_c":8.5,"provenance":"simulated cargo-temperature scenario projection; not observed sensor data or a validated failure-risk model","assumptions":["First-order thermal response; fault time constant 120 minutes, normal control 20 minutes","Normal assumed control equilibrium 2°C, with a small uncalibrated ambient penalty above 30°C","4°C is a conservative demonstration review threshold, not a lot disposition rule","Bands are parameter-sensitivity ranges, not statistical confidence intervals","No pathogen growth, consumer illness probability or automatic hold decision"]}},{"id":"SH03","truck_id":"T01","lot_id":"L02","destination_id":"D03","destination_name":"Simulated test destination D03","quantity_kg":400,"duration_before_hours":5.5,"duration_after_hours":5.5,"deadline_hours":6,"deadline_margin_hours":0.5,"misses_deadline":false,"selected_in_baseline":true,"selected_after_A":true,"exclusion_reasons":[],"temperature":{"checked_hours":5.5,"checkpoint":"at_modeled_arrival","projected_temperature_c":2.0,"max_temperature_c":2.0,"time_above_threshold_minutes":0,"review_required":false,"refrigeration_fault":false,"thermal_control_unavailable":false,"fault_source":"normal refrigeration assumption","initial_temperature_c":1.2,"provenance":"simulated cargo-temperature scenario projection; not observed sensor data or a validated failure-risk model","assumptions":["First-order thermal response; fault time constant 120 minutes, normal control 20 minutes","Normal assumed control equilibrium 2°C, with a small uncalibrated ambient penalty above 30°C","4°C is a conservative demonstration review threshold, not a lot disposition rule","Bands are parameter-sensitivity ranges, not statistical confidence intervals","No pathogen growth, consumer illness probability or automatic hold decision"]}},{"id":"SH04","truck_id":"T02","lot_id":"L02","destination_id":"D04","destination_name":"Simulated test destination D04","quantity_kg":400,"duration_before_hours":5.5,"duration_after_hours":5.5,"deadline_hours":6,"deadline_margin_hours":0.5,"misses_deadline":false,"selected_in_baseline":true,"selected_after_A":true,"exclusion_reasons":[],"temperature":{"checked_hours":5.5,"checkpoint":"at_modeled_arrival","projected_temperature_c":2.0,"max_temperature_c":2.0,"time_above_threshold_minutes":0,"review_required":false,"refrigeration_fault":false,"thermal_control_unavailable":false,"fault_source":"normal refrigeration assumption","initial_temperature_c":1.2,"provenance":"simulated cargo-temperature scenario projection; not observed sensor data or a validated failure-risk model","assumptions":["First-order thermal response; fault time constant 120 minutes, normal control 20 minutes","Normal assumed control equilibrium 2°C, with a small uncalibrated ambient penalty above 30°C","4°C is a conservative demonstration review threshold, not a lot disposition rule","Bands are parameter-sensitivity ranges, not statistical confidence intervals","No pathogen growth, consumer illness probability or automatic hold decision"]}},{"id":"SH05","truck_id":"T01","lot_id":"L02","destination_id":"D05","destination_name":"Simulated test destination D05","quantity_kg":400,"duration_before_hours":5.5,"duration_after_hours":5.5,"deadline_hours":6,"deadline_margin_hours":0.5,"misses_deadline":false,"selected_in_baseline":true,"selected_after_A":true,"exclusion_reasons":[],"temperature":{"checked_hours":5.5,"checkpoint":"at_modeled_arrival","projected_temperature_c":2.0,"max_temperature_c":2.0,"time_above_threshold_minutes":0,"review_required":false,"refrigeration_fault":false,"thermal_control_unavailable":false,"fault_source":"normal refrigeration assumption","initial_temperature_c":1.2,"provenance":"simulated cargo-temperature scenario projection; not observed sensor data or a validated failure-risk model","assumptions":["First-order thermal response; fault time constant 120 minutes, normal control 20 minutes","Normal assumed control equilibrium 2°C, with a small uncalibrated ambient penalty above 30°C","4°C is a conservative demonstration review threshold, not a lot disposition rule","Bands are parameter-sensitivity ranges, not statistical confidence intervals","No pathogen growth, consumer illness probability or automatic hold decision"]}},{"id":"SH06","truck_id":"T02","lot_id":"L02","destination_id":"D06","destination_name":"Simulated test destination D06","quantity_kg":400,"duration_before_hours":5.5,"duration_after_hours":5.5,"deadline_hours":6,"deadline_margin_hours":0.5,"misses_deadline":false,"selected_in_baseline":true,"selected_after_A":true,"exclusion_reasons":[],"temperature":{"checked_hours":5.5,"checkpoint":"at_modeled_arrival","projected_temperature_c":2.0,"max_temperature_c":2.0,"time_above_threshold_minutes":0,"review_required":false,"refrigeration_fault":false,"thermal_control_unavailable":false,"fault_source":"normal refrigeration assumption","initial_temperature_c":1.2,"provenance":"simulated cargo-temperature scenario projection; not observed sensor data or a validated failure-risk model","assumptions":["First-order thermal response; fault time constant 120 minutes, normal control 20 minutes","Normal assumed control equilibrium 2°C, with a small uncalibrated ambient penalty above 30°C","4°C is a conservative demonstration review threshold, not a lot disposition rule","Bands are parameter-sensitivity ranges, not statistical confidence intervals","No pathogen growth, consumer illness probability or automatic hold decision"]}},{"id":"SH07","truck_id":"T01","lot_id":"L02","destination_id":"D07","destination_name":"Simulated test destination D07","quantity_kg":400,"duration_before_hours":5.5,"duration_after_hours":5.5,"deadline_hours":6,"deadline_margin_hours":0.5,"misses_deadline":false,"selected_in_baseline":true,"selected_after_A":true,"exclusion_reasons":[],"temperature":{"checked_hours":5.5,"checkpoint":"at_modeled_arrival","projected_temperature_c":2.0,"max_temperature_c":2.0,"time_above_threshold_minutes":0,"review_required":false,"refrigeration_fault":false,"thermal_control_unavailable":false,"fault_source":"normal refrigeration assumption","initial_temperature_c":1.2,"provenance":"simulated cargo-temperature scenario projection; not observed sensor data or a validated failure-risk model","assumptions":["First-order thermal response; fault time constant 120 minutes, normal control 20 minutes","Normal assumed control equilibrium 2°C, with a small uncalibrated ambient penalty above 30°C","4°C is a conservative demonstration review threshold, not a lot disposition rule","Bands are parameter-sensitivity ranges, not statistical confidence intervals","No pathogen growth, consumer illness probability or automatic hold decision"]}}],"destinations":[{"id":"D01","name":"Simulated test destination D01","demand_kg":500,"supplied_before_kg":0,"supplied_after_kg":0,"unmet_before_kg":500,"unmet_after_kg":500},{"id":"D02","name":"Simulated test destination D02","demand_kg":500,"supplied_before_kg":400,"supplied_after_kg":400,"unmet_before_kg":100,"unmet_after_kg":100},{"id":"D03","name":"Simulated test destination D03","demand_kg":500,"supplied_before_kg":400,"supplied_after_kg":400,"unmet_before_kg":100,"unmet_after_kg":100},{"id":"D04","name":"Simulated test destination D04","demand_kg":500,"supplied_before_kg":400,"supplied_after_kg":400,"unmet_before_kg":100,"unmet_after_kg":100},{"id":"D05","name":"Simulated test destination D05","demand_kg":500,"supplied_before_kg":400,"supplied_after_kg":400,"unmet_before_kg":100,"unmet_after_kg":100},{"id":"D06","name":"Simulated test destination D06","demand_kg":500,"supplied_before_kg":400,"supplied_after_kg":400,"unmet_before_kg":100,"unmet_after_kg":100},{"id":"D07","name":"Simulated test destination D07","demand_kg":500,"supplied_before_kg":400,"supplied_after_kg":400,"unmet_before_kg":100,"unmet_after_kg":100}],"takeaways":["Under these assumptions, scenario A selects 6 of 7 candidate trips and allocates 2,400 kg; 1,100 kg of simulated demand remains unmet.","Compared with the current inputs, these chosen delay/fault assumptions change scenario-A unmet demand by +0 kg. This is an observed planning comparison, not a learned forecast.","0 candidate trips exceed their relative delivery deadlines. Candidate checks include trips that may never be selected.","1 candidates have a modeled temperature above the 4°C demonstration review level during their checked window, capped at six hours. Review flags do not create holds."],"limitations":["This is a relative one-wave simulation with a six-hour thermal check horizon, not today's dispatch schedule, a live ETA or a learned forecast.","Added delay is applied uniformly to every candidate as an explicit planning assumption; it is not estimated from road closures or weather.","Thermal coefficients are uncalibrated. A projected value above the 4°C demonstration review level is not a regulatory finding, pathogen-growth estimate or consumer-illness probability.","Projected temperatures flag candidates for review only. They do not replace current cargo readings, create holds, or enter scenario C as newly observed excursions.","Scenario C holds remain proposed until separate human approval. Held, recalled and ineligible stock stays excluded under every allocation.","Scenario D can substitute eligible simulated lots on fixed trips; no route geometry, stop order or truck assignment is redesigned here.","Candidate counts include trips that may never be selected. Shared stock, capacity, demand, deadlines and eligibility are checked jointly by the actual allocation solver.","Baseline means a newly computed scenario-A allocation of the current inputs, not the current approved driver-assignment list.","Unmet demand and stock are one-wave quantities, not a rolling inventory ledger. Unsent stock is not automatically food waste.","Changed allocations are observed solver comparisons, not a causal proof of why one particular trip was selected.","No event, proposal, assignment, source refresh, model training or approval is performed by this calculation."],"review_links":[{"view":"command","label":"Compare current response plans"},{"view":"roads","label":"Inspect separate road evidence"},{"view":"dispatch","label":"Open human dispatcher review"}]},"delayed":{"kind":"delivery_outlook","snapshot_id":"b988dd924288ef47814581f22ca91b8ee90893e9156832b116797e5ed0ffe51d","network_snapshot_id":"76c41cb5ce8a19112eee88a6d04bb17381e93e902946029312ec8f1d90eeb948","network_revision":3,"generated_at":"2026-10-29T18:00:00+00:00","read_only":true,"simulation":true,"operational_state_modified":false,"planning_horizon_hours":6,"parameters":{"added_delay_minutes":60,"ambient_temperature_c":30.0,"fault_truck_id":null},"provenance":{"model_kind":"deterministic planning projection","network_input":"simulated network and fixed candidate trips; not real supply contracts","weather_input":"user planning assumption; not an observed weather value or fetched forecast","cargo_input":"simulated current cargo temperature; not physical sensor telemetry","travel_input":"fixed origin-destination planning duration, including already recorded simulated delays; no new road routing","model_performance":"No prospective delay or cargo-failure skill is established here. Saved FSIS sampling model evaluation remains a separate scientific task."},"baseline":{"scenario":"A","name":"Baseline distribution","total_logistics_cost":1308,"unmet_demand_kg":1100,"selected_shipments":6,"supplied_kg":2400,"affected_shipments":1,"review_priority_count":1,"food_waste_kg":0,"solver_status":"OPTIMAL","feasible":true,"constraint_violations":0,"constraint_review_passed":true,"proposed_hold_lots":[],"selected_ids":["SH02","SH03","SH04","SH05","SH06","SH07"],"selected_lots":{"SH02":"L02","SH03":"L02","SH04":"L02","SH05":"L02","SH06":"L02","SH07":"L02"},"requires_human_approval":true},"scenarios":[{"scenario":"A","name":"Baseline distribution","summary":{"scenario":"A","name":"Baseline distribution","total_logistics_cost":218,"unmet_demand_kg":3100,"selected_shipments":1,"supplied_kg":400,"affected_shipments":6,"review_priority_count":1,"food_waste_kg":0,"solver_status":"OPTIMAL","feasible":true,"constraint_violations":0,"constraint_review_passed":true,"proposed_hold_lots":[],"selected_ids":["SH02"],"selected_lots":{"SH02":"L02"},"requires_human_approval":true},"delta_vs_baseline":{"total_logistics_cost":-1090,"unmet_demand_kg":2000,"selected_shipments":-5,"supplied_kg":-2000,"affected_shipments":5,"review_priority_count":0,"food_waste_kg":0}},{"scenario":"B","name":"Targeted verification","summary":{"scenario":"B","name":"Targeted verification","total_logistics_cost":293,"unmet_demand_kg":3100,"selected_shipments":1,"supplied_kg":400,"affected_shipments":6,"review_priority_count":1,"food_waste_kg":0,"solver_status":"OPTIMAL","feasible":true,"constraint_violations":0,"constraint_review_passed":true,"proposed_hold_lots":[],"selected_ids":["SH02"],"selected_lots":{"SH02":"L02"},"requires_human_approval":true},"delta_vs_baseline":{"total_logistics_cost":-1015,"unmet_demand_kg":2000,"selected_shipments":-5,"supplied_kg":-2000,"affected_shipments":5,"review_priority_count":0,"food_waste_kg":0}},{"scenario":"C","name":"Precautionary hold pending review","summary":{"scenario":"C","name":"Precautionary hold pending review","total_logistics_cost":0,"unmet_demand_kg":3500,"selected_shipments":0,"supplied_kg":0,"affected_shipments":7,"review_priority_count":0,"food_waste_kg":0,"solver_status":"OPTIMAL","feasible":true,"constraint_violations":0,"constraint_review_passed":true,"proposed_hold_lots":["L02"],"selected_ids":[],"selected_lots":{},"requires_human_approval":true},"delta_vs_baseline":{"total_logistics_cost":-1308,"unmet_demand_kg":2400,"selected_shipments":-6,"supplied_kg":-2400,"affected_shipments":6,"review_priority_count":-1,"food_waste_kg":0}},{"scenario":"D","name":"Alternative eligible supply","summary":{"scenario":"D","name":"Alternative eligible supply","total_logistics_cost":481,"unmet_demand_kg":2700,"selected_shipments":2,"supplied_kg":800,"affected_shipments":5,"review_priority_count":1,"food_waste_kg":0,"solver_status":"OPTIMAL","feasible":true,"constraint_violations":0,"constraint_review_passed":true,"proposed_hold_lots":[],"selected_ids":["SH01","SH02"],"selected_lots":{"SH01":"L02","SH02":"L02"},"requires_human_approval":true},"delta_vs_baseline":{"total_logistics_cost":-827,"unmet_demand_kg":1600,"selected_shipments":-4,"supplied_kg":-1600,"affected_shipments":4,"review_priority_count":0,"food_waste_kg":0}}],"summary":{"total_demand_kg":3500,"before_unmet_demand_kg":1100,"after_unmet_demand_kg":3100,"unmet_demand_change_kg":2000,"selected_shipments_before":6,"selected_shipments_after":1,"candidate_deadline_misses":5,"candidate_temperature_reviews":1,"candidate_shipments":7},"shipments":[{"id":"SH01","truck_id":"T01","lot_id":"L01","destination_id":"D01","destination_name":"Simulated test destination D01","quantity_kg":400,"duration_before_hours":1.5,"duration_after_hours":2.5,"deadline_hours":6,"deadline_margin_hours":3.5,"misses_deadline":false,"selected_in_baseline":false,"selected_after_A":false,"exclusion_reasons":["lot held"],"temperature":{"checked_hours":2.5,"checkpoint":"at_modeled_arrival","projected_temperature_c":2.0,"max_temperature_c":2.0,"time_above_threshold_minutes":0,"review_required":false,"refrigeration_fault":false,"thermal_control_unavailable":false,"fault_source":"normal refrigeration assumption","initial_temperature_c":1.2,"provenance":"simulated cargo-temperature scenario projection; not observed sensor data or a validated failure-risk model","assumptions":["First-order thermal response; fault time constant 120 minutes, normal control 20 minutes","Normal assumed control equilibrium 2°C, with a small uncalibrated ambient penalty above 30°C","4°C is a conservative demonstration review threshold, not a lot disposition rule","Bands are parameter-sensitivity ranges, not statistical confidence intervals","No pathogen growth, consumer illness probability or automatic hold decision"]}},{"id":"SH02","truck_id":"T02","lot_id":"L02","destination_id":"D02","destination_name":"Simulated test destination D02","quantity_kg":400,"duration_before_hours":2,"duration_after_hours":3.0,"deadline_hours":6,"deadline_margin_hours":3.0,"misses_deadline":false,"selected_in_baseline":true,"selected_after_A":true,"exclusion_reasons":[],"temperature":{"checked_hours":3.0,"checkpoint":"at_modeled_arrival","projected_temperature_c":2.001,"max_temperature_c":8.5,"time_above_threshold_minutes":23.57,"review_required":true,"refrigeration_fault":false,"thermal_control_unavailable":false,"fault_source":"normal refrigeration assumption","initial_temperature_c":8.5,"provenance":"simulated cargo-temperature scenario projection; not observed sensor data or a validated failure-risk model","assumptions":["First-order thermal response; fault time constant 120 minutes, normal control 20 minutes","Normal assumed control equilibrium 2°C, with a small uncalibrated ambient penalty above 30°C","4°C is a conservative demonstration review threshold, not a lot disposition rule","Bands are parameter-sensitivity ranges, not statistical confidence intervals","No pathogen growth, consumer illness probability or automatic hold decision"]}},{"id":"SH03","truck_id":"T01","lot_id":"L02","destination_id":"D03","destination_name":"Simulated test destination D03","quantity_kg":400,"duration_before_hours":5.5,"duration_after_hours":6.5,"deadline_hours":6,"deadline_margin_hours":-0.5,"misses_deadline":true,"selected_in_baseline":true,"selected_after_A":false,"exclusion_reasons":["delivery deadline exceeded"],"temperature":{"checked_hours":6,"checkpoint":"at_6h_horizon","projected_temperature_c":2.0,"max_temperature_c":2.0,"time_above_threshold_minutes":0,"review_required":false,"refrigeration_fault":false,"thermal_control_unavailable":false,"fault_source":"normal refrigeration assumption","initial_temperature_c":1.2,"provenance":"simulated cargo-temperature scenario projection; not observed sensor data or a validated failure-risk model","assumptions":["First-order thermal response; fault time constant 120 minutes, normal control 20 minutes","Normal assumed control equilibrium 2°C, with a small uncalibrated ambient penalty above 30°C","4°C is a conservative demonstration review threshold, not a lot disposition rule","Bands are parameter-sensitivity ranges, not statistical confidence intervals","No pathogen growth, consumer illness probability or automatic hold decision"]}},{"id":"SH04","truck_id":"T02","lot_id":"L02","destination_id":"D04","destination_name":"Simulated test destination D04","quantity_kg":400,"duration_before_hours":5.5,"duration_after_hours":6.5,"deadline_hours":6,"deadline_margin_hours":-0.5,"misses_deadline":true,"selected_in_baseline":true,"selected_after_A":false,"exclusion_reasons":["delivery deadline exceeded"],"temperature":{"checked_hours":6,"checkpoint":"at_6h_horizon","projected_temperature_c":2.0,"max_temperature_c":2.0,"time_above_threshold_minutes":0,"review_required":false,"refrigeration_fault":false,"thermal_control_unavailable":false,"fault_source":"normal refrigeration assumption","initial_temperature_c":1.2,"provenance":"simulated cargo-temperature scenario projection; not observed sensor data or a validated failure-risk model","assumptions":["First-order thermal response; fault time constant 120 minutes, normal control 20 minutes","Normal assumed control equilibrium 2°C, with a small uncalibrated ambient penalty above 30°C","4°C is a conservative demonstration review threshold, not a lot disposition rule","Bands are parameter-sensitivity ranges, not statistical confidence intervals","No pathogen growth, consumer illness probability or automatic hold decision"]}},{"id":"SH05","truck_id":"T01","lot_id":"L02","destination_id":"D05","destination_name":"Simulated test destination D05","quantity_kg":400,"duration_before_hours":5.5,"duration_after_hours":6.5,"deadline_hours":6,"deadline_margin_hours":-0.5,"misses_deadline":true,"selected_in_baseline":true,"selected_after_A":false,"exclusion_reasons":["delivery deadline exceeded"],"temperature":{"checked_hours":6,"checkpoint":"at_6h_horizon","projected_temperature_c":2.0,"max_temperature_c":2.0,"time_above_threshold_minutes":0,"review_required":false,"refrigeration_fault":false,"thermal_control_unavailable":false,"fault_source":"normal refrigeration assumption","initial_temperature_c":1.2,"provenance":"simulated cargo-temperature scenario projection; not observed sensor data or a validated failure-risk model","assumptions":["First-order thermal response; fault time constant 120 minutes, normal control 20 minutes","Normal assumed control equilibrium 2°C, with a small uncalibrated ambient penalty above 30°C","4°C is a conservative demonstration review threshold, not a lot disposition rule","Bands are parameter-sensitivity ranges, not statistical confidence intervals","No pathogen growth, consumer illness probability or automatic hold decision"]}},{"id":"SH06","truck_id":"T02","lot_id":"L02","destination_id":"D06","destination_name":"Simulated test destination D06","quantity_kg":400,"duration_before_hours":5.5,"duration_after_hours":6.5,"deadline_hours":6,"deadline_margin_hours":-0.5,"misses_deadline":true,"selected_in_baseline":true,"selected_after_A":false,"exclusion_reasons":["delivery deadline exceeded"],"temperature":{"checked_hours":6,"checkpoint":"at_6h_horizon","projected_temperature_c":2.0,"max_temperature_c":2.0,"time_above_threshold_minutes":0,"review_required":false,"refrigeration_fault":false,"thermal_control_unavailable":false,"fault_source":"normal refrigeration assumption","initial_temperature_c":1.2,"provenance":"simulated cargo-temperature scenario projection; not observed sensor data or a validated failure-risk model","assumptions":["First-order thermal response; fault time constant 120 minutes, normal control 20 minutes","Normal assumed control equilibrium 2°C, with a small uncalibrated ambient penalty above 30°C","4°C is a conservative demonstration review threshold, not a lot disposition rule","Bands are parameter-sensitivity ranges, not statistical confidence intervals","No pathogen growth, consumer illness probability or automatic hold decision"]}},{"id":"SH07","truck_id":"T01","lot_id":"L02","destination_id":"D07","destination_name":"Simulated test destination D07","quantity_kg":400,"duration_before_hours":5.5,"duration_after_hours":6.5,"deadline_hours":6,"deadline_margin_hours":-0.5,"misses_deadline":true,"selected_in_baseline":true,"selected_after_A":false,"exclusion_reasons":["delivery deadline exceeded"],"temperature":{"checked_hours":6,"checkpoint":"at_6h_horizon","projected_temperature_c":2.0,"max_temperature_c":2.0,"time_above_threshold_minutes":0,"review_required":false,"refrigeration_fault":false,"thermal_control_unavailable":false,"fault_source":"normal refrigeration assumption","initial_temperature_c":1.2,"provenance":"simulated cargo-temperature scenario projection; not observed sensor data or a validated failure-risk model","assumptions":["First-order thermal response; fault time constant 120 minutes, normal control 20 minutes","Normal assumed control equilibrium 2°C, with a small uncalibrated ambient penalty above 30°C","4°C is a conservative demonstration review threshold, not a lot disposition rule","Bands are parameter-sensitivity ranges, not statistical confidence intervals","No pathogen growth, consumer illness probability or automatic hold decision"]}}],"destinations":[{"id":"D01","name":"Simulated test destination D01","demand_kg":500,"supplied_before_kg":0,"supplied_after_kg":0,"unmet_before_kg":500,"unmet_after_kg":500},{"id":"D02","name":"Simulated test destination D02","demand_kg":500,"supplied_before_kg":400,"supplied_after_kg":400,"unmet_before_kg":100,"unmet_after_kg":100},{"id":"D03","name":"Simulated test destination D03","demand_kg":500,"supplied_before_kg":400,"supplied_after_kg":0,"unmet_before_kg":100,"unmet_after_kg":500},{"id":"D04","name":"Simulated test destination D04","demand_kg":500,"supplied_before_kg":400,"supplied_after_kg":0,"unmet_before_kg":100,"unmet_after_kg":500},{"id":"D05","name":"Simulated test destination D05","demand_kg":500,"supplied_before_kg":400,"supplied_after_kg":0,"unmet_before_kg":100,"unmet_after_kg":500},{"id":"D06","name":"Simulated test destination D06","demand_kg":500,"supplied_before_kg":400,"supplied_after_kg":0,"unmet_before_kg":100,"unmet_after_kg":500},{"id":"D07","name":"Simulated test destination D07","demand_kg":500,"supplied_before_kg":400,"supplied_after_kg":0,"unmet_before_kg":100,"unmet_after_kg":500}],"takeaways":["Under these assumptions, scenario A selects 1 of 7 candidate trips and allocates 400 kg; 3,100 kg of simulated demand remains unmet.","Compared with the current inputs, these chosen delay/fault assumptions change scenario-A unmet demand by +2,000 kg. This is an observed planning comparison, not a learned forecast.","5 candidate trips exceed their relative delivery deadlines. Candidate checks include trips that may never be selected.","1 candidates have a modeled temperature above the 4°C demonstration review level during their checked window, capped at six hours. Review flags do not create holds."],"limitations":["This is a relative one-wave simulation with a six-hour thermal check horizon, not today's dispatch schedule, a live ETA or a learned forecast.","Added delay is applied uniformly to every candidate as an explicit planning assumption; it is not estimated from road closures or weather.","Thermal coefficients are uncalibrated. A projected value above the 4°C demonstration review level is not a regulatory finding, pathogen-growth estimate or consumer-illness probability.","Projected temperatures flag candidates for review only. They do not replace current cargo readings, create holds, or enter scenario C as newly observed excursions.","Scenario C holds remain proposed until separate human approval. Held, recalled and ineligible stock stays excluded under every allocation.","Scenario D can substitute eligible simulated lots on fixed trips; no route geometry, stop order or truck assignment is redesigned here.","Candidate counts include trips that may never be selected. Shared stock, capacity, demand, deadlines and eligibility are checked jointly by the actual allocation solver.","Baseline means a newly computed scenario-A allocation of the current inputs, not the current approved driver-assignment list.","Unmet demand and stock are one-wave quantities, not a rolling inventory ledger. Unsent stock is not automatically food waste.","Changed allocations are observed solver comparisons, not a causal proof of why one particular trip was selected.","No event, proposal, assignment, source refresh, model training or approval is performed by this calculation."],"review_links":[{"view":"command","label":"Compare current response plans"},{"view":"roads","label":"Inspect separate road evidence"},{"view":"dispatch","label":"Open human dispatcher review"}]}};

const network: Network = {
  ...captured.network,
  nodes: captured.network.nodes.map((node): Network['nodes'][number] => ({
    ...node, coordinates: [node.coordinates[0], node.coordinates[1]],
  })),
};
function response(delay = 0) { return structuredClone(delay === 60 ? captured.delayed : captured.baseline); }
// Actual helper output differs only in these captured fields when the same
// seven-trip simulation uses 35°C ambient and otherwise unchanged assumptions.
function ambientResponse() {
  const value = response();
  value.snapshot_id = '46f296bc6aec606b2dc1a3f9b3daffbb7c1a209f2e14aaea92c78e6c45cbf12f';
  value.parameters.ambient_temperature_c = 35;
  const changes = [
    { projected_temperature_c: 2.139, max_temperature_c: 2.139 },
    { projected_temperature_c: 2.166, time_above_threshold_minutes: 24.67 },
    ...Array.from({ length: 5 }, () => ({ projected_temperature_c: 2.15, max_temperature_c: 2.15 })),
  ];
  value.shipments.forEach((row, index) => Object.assign(row.temperature, changes[index]));
  return value;
}
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (reason: Error) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }
function mount(overrides: Record<string, any> = {}) {
  const props = { network, onInspectShipment: vi.fn(), onNavigate: vi.fn(), onReloadNetwork: vi.fn().mockResolvedValue(undefined), ...overrides };
  return { ...render(<DeliveryOutlook {...props} />), props };
}
async function settled() { return screen.findByRole('button', { name: 'Export outlook JSON' }); }
async function click(name: string) { await act(async () => { fireEvent.click(screen.getByRole('button', { name })); }); }
function metric(label: string) { return within(screen.getByText(label, { selector: 'article > span' }).closest('article')!); }
function ambient() { return screen.getByRole('spinbutton', { name: /Ambient temperature assumption/ }); }
function fault() { return screen.getByRole('combobox', { name: 'Assumed refrigeration fault' }); }
function openAssumptions() { fireEvent.click(screen.getByText('Cargo assumptions')); }
function assertReadOnly() {
  expect(vi.mocked(api).mock.calls.every(([path]) => path === '/delivery-outlook')).toBe(true);
  expect(screen.queryByRole('button', { name: /approve|apply|dispatch|hold|send instruction/i })).not.toBeInTheDocument();
}
beforeEach(() => {
  vi.mocked(api).mockReset(); vi.mocked(downloadCaptured).mockReset();
  vi.mocked(api).mockImplementation(async (path, body: any): Promise<any> => {
    if (path !== '/delivery-outlook') throw new Error('Unexpected mocked endpoint: ' + path);
    if (body.ambient_temperature_c !== 30 || body.fault_truck_id !== null || ![0, 60].includes(body.added_delay_minutes)) throw new Error('No captured backend fixture for these test-only assumptions');
    return response(body.added_delay_minutes);
  });
});

it('automatically computes one current-input estimate with real captured allocation and thermal results', async () => {
  mount(); await settled();
  expect(api).toHaveBeenCalledExactlyOnceWith('/delivery-outlook', { expected_network_revision: 3, added_delay_minutes: 0, ambient_temperature_c: 30, fault_truck_id: null });
  expect(metric('Unserved demand').getByText('1,100 kg')).toBeInTheDocument();
  expect(metric('Unserved demand').getByText(/Current inputs: 1,100 kg/)).toHaveTextContent('change 0 kg');
  expect(metric('Deadline pressure').getByText('0 candidate trips')).toBeInTheDocument();
  expect(metric('Cargo checks').getByText('1 candidate trips')).toBeInTheDocument();
  expect(screen.getByText(/The allocation selects 6 of 7 candidates/)).toBeInTheDocument();
  expect(screen.getByText(/Current-input estimate/)).toHaveTextContent('revision 3');
  expect(screen.getByText(/routes, inventory, holds and driver assignments have not changed/)).toBeInTheDocument();
  assertReadOnly();
});

it('shows six priority candidates, expands all, and navigates an inspection without changing any state', async () => {
  const view = mount(); await settled();
  const table = screen.getAllByRole('table')[0];
  expect(within(table).getAllByRole('row')).toHaveLength(7);
  const firstInspection = within(table).getAllByRole('button', { name: /^Inspect SH/ })[0];
  expect(firstInspection).toHaveAccessibleName('Inspect SH02');
  fireEvent.click(firstInspection);
  expect(view.props.onInspectShipment).toHaveBeenCalledExactlyOnceWith('SH02');
  await click('Show all 7 candidates');
  expect(within(table).getAllByRole('row')).toHaveLength(8);
  await click('Show priority trips');
  expect(within(table).getAllByRole('row')).toHaveLength(7);
  await click('Check road alternatives');
  expect(view.props.onNavigate).toHaveBeenCalledExactlyOnceWith('roads');
  expect(api).toHaveBeenCalledTimes(1); assertReadOnly();
});

it('offers current-plan review and road comparison for the exact candidate without recalculating or changing the capture', async () => {
  const review = vi.fn(), roads = vi.fn();
  const originalNetwork = structuredClone(network);
  const view = mount({ onReviewPlans: review, onCompareShipmentRoad: roads }); await settled();
  expect(screen.getByText(/Review opens response plans for the current network/)).toHaveTextContent('approval is a separate step');
  await click('Review current response plans');
  expect(review).toHaveBeenCalledExactlyOnceWith();
  await click('Compare roads for SH02');
  expect(roads).toHaveBeenCalledExactlyOnceWith('SH02');
  expect(view.props.onInspectShipment).not.toHaveBeenCalled();
  expect(view.props.onNavigate).not.toHaveBeenCalled();
  await click('Show all 7 candidates');
  await click('Compare roads for SH01');
  expect(roads.mock.calls).toEqual([['SH02'], ['SH01']]);
  await click('Export outlook JSON');
  expect(downloadCaptured).toHaveBeenCalledExactlyOnceWith('aegis-delivery-outlook.json', { ...captured.baseline, captured_export: true });
  expect(network).toEqual(originalNetwork);
  expect(api).toHaveBeenCalledTimes(1); assertReadOnly();
});

it('lets a changed draft open the current plan while keeping the uncomputed assumptions out of the captured result', async () => {
  const review = vi.fn(), roads = vi.fn();
  mount({ onReviewPlans: review, onCompareShipmentRoad: roads }); await settled();
  fireEvent.change(screen.getByRole('combobox', { name: 'Extra road delay' }), { target: { value: '60' } });
  expect(screen.getByRole('status')).toHaveTextContent(/Assumptions changed/);
  await click('Review current response plans');
  await click('Compare roads for SH02');
  expect(review).toHaveBeenCalledExactlyOnceWith();
  expect(roads).toHaveBeenCalledExactlyOnceWith('SH02');
  expect(screen.getByText(/Current-input estimate/)).toHaveTextContent('0 extra minutes');
  expect(metric('Unserved demand').getByText('1,100 kg')).toBeInTheDocument();
  await click('Export outlook JSON');
  expect(downloadCaptured).toHaveBeenCalledExactlyOnceWith('aegis-delivery-outlook.json', { ...captured.baseline, captured_export: true });
  expect(api).toHaveBeenCalledTimes(1); assertReadOnly();
});

it('describes computed what-if assumptions as separate from current-plan review and preserves their captured export', async () => {
  const review = vi.fn(), roads = vi.fn();
  const originalNetwork = structuredClone(network);
  mount({ onReviewPlans: review, onCompareShipmentRoad: roads }); await settled();
  await click('Try a 1-hour delay');
  expect(screen.getByText(/What-if estimate/)).toHaveTextContent('60 extra minutes');
  expect(screen.getByText(/Review opens response plans for the current network/)).toHaveTextContent('Extra delay and cargo assumptions stay in this estimate');
  await click('Review current response plans');
  await click('Compare roads for SH02');
  expect(review).toHaveBeenCalledExactlyOnceWith();
  expect(roads).toHaveBeenCalledExactlyOnceWith('SH02');
  await click('Export outlook JSON');
  expect(downloadCaptured).toHaveBeenCalledExactlyOnceWith('aegis-delivery-outlook.json', { ...captured.delayed, captured_export: true });
  expect(network).toEqual(originalNetwork);
  expect(api).toHaveBeenCalledTimes(2); assertReadOnly();
});

it('disables navigation from an older network revision while preserving its captured export', async () => {
  const review = vi.fn(), roads = vi.fn();
  const view = mount({ onReviewPlans: review, onCompareShipmentRoad: roads }); await settled();
  view.rerender(<DeliveryOutlook {...view.props} onReviewPlans={review} onCompareShipmentRoad={roads} network={{ ...network, revision: 4 }} />);
  for (const name of ['Review current response plans', 'Check road alternatives', 'Inspect SH02', 'Compare roads for SH02']) {
    expect(screen.getByRole('button', { name })).toBeDisabled();
    await click(name);
  }
  expect(screen.getByText(/Calculate an updated estimate before opening trips or response plans/)).toBeInTheDocument();
  expect(review).not.toHaveBeenCalled(); expect(roads).not.toHaveBeenCalled();
  expect(view.props.onNavigate).not.toHaveBeenCalled(); expect(view.props.onInspectShipment).not.toHaveBeenCalled();
  expect(screen.getByRole('button', { name: 'Export outlook JSON' })).toBeEnabled();
  await click('Export outlook JSON');
  expect(downloadCaptured).toHaveBeenCalledExactlyOnceWith('aegis-delivery-outlook.json', { ...captured.baseline, captured_export: true });
  expect(api).toHaveBeenCalledTimes(1); assertReadOnly();
});

it('blocks a missing candidate by identity without blocking other current candidate inspections', async () => {
  const roads = vi.fn();
  const view = mount({ onCompareShipmentRoad: roads }); await settled();
  view.rerender(<DeliveryOutlook {...view.props} onCompareShipmentRoad={roads} network={{ ...network, shipments: network.shipments.filter(shipment => shipment.id !== 'SH02') }} />);
  expect(screen.getByRole('button', { name: 'Inspect SH02' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Compare roads for SH02' })).toBeDisabled();
  expect(screen.getByText(/This candidate is no longer in the current network/)).toBeInTheDocument();
  await click('Inspect SH02'); await click('Compare roads for SH02');
  expect(view.props.onInspectShipment).not.toHaveBeenCalled(); expect(roads).not.toHaveBeenCalled();
  await click('Inspect SH03'); await click('Compare roads for SH03');
  expect(view.props.onInspectShipment).toHaveBeenCalledExactlyOnceWith('SH03');
  expect(roads).toHaveBeenCalledExactlyOnceWith('SH03');
  await click('Export outlook JSON');
  expect(downloadCaptured).toHaveBeenCalledExactlyOnceWith('aegis-delivery-outlook.json', { ...captured.baseline, captured_export: true });
  expect(api).toHaveBeenCalledTimes(1); assertReadOnly();
});

it('does not offer optional callback controls as inactive buttons when their workspaces are unavailable', async () => {
  mount({ onInspectShipment: undefined, onNavigate: undefined }); await settled();
  expect(screen.queryByRole('button', { name: 'Review current response plans' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /^Compare roads for SH/ })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Inspect SH02' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Check road alternatives' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Export outlook JSON' })).toBeEnabled();
  expect(api).toHaveBeenCalledTimes(1); assertReadOnly();
});

it('keeps edited assumptions separate from the captured estimate until Estimate impact is clicked', async () => {
  mount(); await settled();
  fireEvent.change(screen.getByRole('combobox', { name: 'Extra road delay' }), { target: { value: '60' } });
  expect(api).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('status')).toHaveTextContent(/Assumptions changed/);
  expect(metric('Unserved demand').getByText('1,100 kg')).toBeInTheDocument();
  await click('Estimate impact');
  expect(api).toHaveBeenLastCalledWith('/delivery-outlook', { expected_network_revision: 3, added_delay_minutes: 60, ambient_temperature_c: 30, fault_truck_id: null });
  expect(metric('Unserved demand').getByText('3,100 kg')).toBeInTheDocument();
  expect(metric('Unserved demand').getByText(/Current inputs: 1,100 kg/)).toHaveTextContent('change +2,000 kg');
  expect(metric('Deadline pressure').getByText('5 candidate trips')).toBeInTheDocument();
  expect(screen.getByText(/The allocation selects 1 of 7 candidates/)).toBeInTheDocument();
  expect(screen.getByText(/What-if estimate/)).toHaveTextContent('60 extra minutes');
  expect(screen.queryByText(/Assumptions changed/)).not.toBeInTheDocument();
  assertReadOnly();
});

it('runs the one-hour shortcut immediately and current-input check resets all planning assumptions', async () => {
  mount(); await settled();
  await click('Try a 1-hour delay');
  expect(api).toHaveBeenCalledTimes(2);
  expect(vi.mocked(api).mock.calls[1][1]).toMatchObject({ added_delay_minutes: 60 });
  expect(screen.getByRole('combobox', { name: 'Extra road delay' })).toHaveValue('60');
  expect(metric('Unserved demand').getByText('3,100 kg')).toBeInTheDocument();
  openAssumptions();
  fireEvent.change(ambient(), { target: { value: '35' } });
  fireEvent.change(fault(), { target: { value: 'T02' } });
  expect(api).toHaveBeenCalledTimes(2);
  await click('Check current inputs');
  expect(api).toHaveBeenLastCalledWith('/delivery-outlook', { expected_network_revision: 3, added_delay_minutes: 0, ambient_temperature_c: 30, fault_truck_id: null });
  expect(screen.getByRole('combobox', { name: 'Extra road delay' })).toHaveValue('0');
  expect(ambient()).toHaveValue(30); expect(fault()).toHaveValue('');
  expect(metric('Unserved demand').getByText('1,100 kg')).toBeInTheDocument();
  assertReadOnly();
});

it('exports the captured result and parameters rather than the uncomputed draft', async () => {
  mount(); await settled(); openAssumptions();
  fireEvent.change(screen.getByRole('combobox', { name: 'Extra road delay' }), { target: { value: '120' } });
  fireEvent.change(ambient(), { target: { value: '35' } });
  fireEvent.change(fault(), { target: { value: 'T02' } });
  await click('Export outlook JSON');
  expect(downloadCaptured).toHaveBeenCalledExactlyOnceWith('aegis-delivery-outlook.json', { ...captured.baseline, captured_export: true });
  const exported = vi.mocked(downloadCaptured).mock.calls[0][1] as any;
  expect(exported.parameters).toEqual({ added_delay_minutes: 0, ambient_temperature_c: 30, fault_truck_id: null });
  expect(exported.operational_state_modified).toBe(false);
  expect(exported.summary.after_unmet_demand_kg).toBe(1100);
  expect(api).toHaveBeenCalledTimes(1); assertReadOnly();
});

it('identifies a temperature-only assumption as what-if and shows the captured assumptions after further edits', async () => {
  mount(); await settled(); openAssumptions();
  expect(screen.getByText(/Current-input estimate/)).toHaveTextContent('captured ambient assumption 30°C');
  fireEvent.change(ambient(), { target: { value: '35' } });
  vi.mocked(api).mockResolvedValueOnce(ambientResponse());
  await click('Estimate impact');
  expect(screen.getByText(/What-if estimate/)).toHaveTextContent('captured ambient assumption 35°C');
  expect(screen.getByText(/What-if estimate/)).toHaveTextContent('no additional fault');
  expect(screen.queryByText(/Current-input estimate/)).not.toBeInTheDocument();
  fireEvent.change(ambient(), { target: { value: '40' } });
  expect(screen.getByText(/What-if estimate/)).toHaveTextContent('captured ambient assumption 35°C');
  expect(screen.getByRole('status')).toHaveTextContent(/displayed result and export still use the captured inputs/);
  await click('Export outlook JSON');
  expect((vi.mocked(downloadCaptured).mock.calls[0][1] as any).parameters.ambient_temperature_c).toBe(35);
  expect(api).toHaveBeenCalledTimes(2); assertReadOnly();
});

it('explains an initially warm cargo review even when the modeled arrival temperature has cooled below 4°C', async () => {
  mount(); await settled(); openAssumptions();
  fireEvent.change(ambient(), { target: { value: '35' } });
  vi.mocked(api).mockResolvedValueOnce(ambientResponse());
  await click('Estimate impact');
  const trip = screen.getByRole('button', { name: 'Inspect SH02' }).closest('tr')!;
  expect(within(trip).getByText(/2\.2°C at modeled arrival/)).toBeInTheDocument();
  expect(within(trip).getByText('Review: peak 8.5°C · 24.7 min above 4°C')).toBeInTheDocument();
  expect(screen.getAllByText('Within the assumed control target').length).toBeGreaterThan(0);
  expect(api).toHaveBeenCalledTimes(2); assertReadOnly();
});

it('submits the selected known truck and ambient assumption only on an explicit calculation', async () => {
  mount(); await settled(); openAssumptions();
  expect(within(fault()).getAllByRole('option').map(option => option.getAttribute('value'))).toEqual(['', 'T01', 'T02']);
  fireEvent.change(ambient(), { target: { value: '35' } });
  fireEvent.change(fault(), { target: { value: 'T02' } });
  expect(api).toHaveBeenCalledTimes(1);
  vi.mocked(api).mockRejectedValueOnce(Object.assign(new Error('Unit-test backend rejection; no outlook produced'), { status: 422 }));
  await click('Estimate impact');
  expect(api).toHaveBeenLastCalledWith('/delivery-outlook', { expected_network_revision: 3, added_delay_minutes: 0, ambient_temperature_c: 35, fault_truck_id: 'T02' });
  expect(screen.getByRole('alert')).toHaveTextContent('no outlook produced');
  assertReadOnly();
});

it('reveals all four actual solver comparisons and the precise boundary on proposed holds', async () => {
  mount(); await settled();
  fireEvent.click(screen.getByText('Compare the four preview responses'));
  const details = screen.getByText('Compare the four preview responses').closest('details')!;
  const rows = within(details).getAllByRole('row');
  expect(rows).toHaveLength(5);
  captured.baseline.scenarios.forEach((scenario, index) => {
    expect(rows[index + 1]).toHaveTextContent(scenario.name);
    expect(rows[index + 1]).toHaveTextContent(`${scenario.summary.unmet_demand_kg} kg`);
    expect(rows[index + 1]).toHaveTextContent(`${scenario.summary.solver_status}`);
  });
  expect(within(details).getByText(/not approved assignments or newly applied holds/)).toBeInTheDocument();
  fireEvent.click(screen.getByText('How this estimate works'));
  expect(screen.getByText(/Projected temperatures flag candidates for review only/)).toBeInTheDocument();
  expect(screen.getByText(/baseline means a newly computed scenario-A allocation/i)).toBeInTheDocument();
  expect(api).toHaveBeenCalledTimes(1); assertReadOnly();
});

it.each(['', '-21', '46'])('rejects an invalid ambient draft %j without another request', async value => {
  mount(); await settled(); openAssumptions();
  fireEvent.change(ambient(), { target: { value } });
  expect(screen.getByRole('alert')).toHaveTextContent(/Choose a temperature/);
  expect(screen.getByRole('button', { name: 'Estimate impact' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Estimate impact' }));
  expect(api).toHaveBeenCalledTimes(1);
});

it.each([
  ['wrong response kind', (value: any) => { value.kind = 'forecast'; }],
  ['wrong revision', (value: any) => { value.network_revision = 4; }],
  ['invalid snapshot', (value: any) => { value.snapshot_id = 'not-a-hash'; }],
  ['invalid source snapshot', (value: any) => { value.network_snapshot_id = 'not-a-hash'; }],
  ['mutable operational state', (value: any) => { value.operational_state_modified = true; }],
  ['unlabeled simulation', (value: any) => { value.simulation = false; }],
  ['different delay', (value: any) => { value.parameters.added_delay_minutes = 60; }],
  ['different ambient assumption', (value: any) => { value.parameters.ambient_temperature_c = 35; }],
  ['different truck fault', (value: any) => { value.parameters.fault_truck_id = 'T02'; }],
  ['different horizon', (value: any) => { value.planning_horizon_hours = 24; }],
  ['missing weather provenance', (value: any) => { delete value.provenance.weather_input; }],
  ['missing cargo provenance', (value: any) => { delete value.provenance.cargo_input; }],
  ['unsupported model claim', (value: any) => { value.provenance.model_kind = 'validated prediction'; }],
  ['nonfinite summary', (value: any) => { value.summary.after_unmet_demand_kg = NaN; }],
  ['failed baseline review', (value: any) => { value.baseline.constraint_review_passed = false; }],
  ['missing candidate checks', (value: any) => { delete value.shipments[0].temperature; }],
  ['nonfinite cargo projection', (value: any) => { value.shipments[0].temperature.projected_temperature_c = Infinity; }],
  ['missing thermal provenance', (value: any) => { delete value.shipments[0].temperature.provenance; }],
  ['unsupported temperature checkpoint', (value: any) => { value.shipments[0].temperature.checkpoint = 'live_arrival'; }],
  ['too many candidates', (value: any) => { value.shipments = Array.from({ length: 51 }, () => value.shipments[0]); }],
  ['missing response option', (value: any) => { value.scenarios.pop(); }],
  ['infeasible allocation', (value: any) => { value.scenarios[0].summary.feasible = false; }],
  ['failed independent review', (value: any) => { value.scenarios[0].summary.constraint_review_passed = false; }],
  ['allocation violation', (value: any) => { value.scenarios[0].summary.constraint_violations = 1; }],
  ['nonfinite destination quantity', (value: any) => { value.destinations[0].unmet_after_kg = Infinity; }],
] as const)('rejects an unverifiable estimate: %s', async (_description, modify) => {
  const invalid = response(); modify(invalid); vi.mocked(api).mockResolvedValueOnce(invalid);
  mount();
  expect(await screen.findByRole('alert')).toHaveTextContent(/could not be verified|invalid|unsupported/i);
  expect(screen.queryByRole('button', { name: 'Export outlook JSON' })).not.toBeInTheDocument();
  expect(screen.queryByText(/The allocation selects/)).not.toBeInTheDocument();
  expect(api).toHaveBeenCalledTimes(1); assertReadOnly();
});

it('keeps pending requests single-flight and exposes backend failure without a fabricated estimate', async () => {
  const pending = deferred<any>(); vi.mocked(api).mockReturnValueOnce(pending.promise);
  mount();
  expect(screen.getByRole('status')).toHaveTextContent(/Checking delivery windows/);
  expect(screen.getByRole('button', { name: /Estimating impact/ })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Try a 1-hour delay' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Try a 1-hour delay' }));
  expect(api).toHaveBeenCalledTimes(1);
  await act(async () => { pending.reject(new Error('No feasible calculation was returned')); });
  expect(screen.getByRole('alert')).toHaveTextContent('No feasible calculation was returned');
  expect(screen.queryByRole('button', { name: 'Export outlook JSON' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Estimate impact' })).toBeEnabled();
  assertReadOnly();
});

it('explains a 409 and reloads only through the explicit refresh button', async () => {
  vi.mocked(api).mockRejectedValueOnce(Object.assign(new Error('Raw conflict'), { status: 409 }));
  const view = mount();
  expect(await screen.findByRole('alert')).toHaveTextContent(/plan changed.*Reload the current plan/i);
  expect(view.props.onReloadNetwork).not.toHaveBeenCalled();
  await click('Reload current plan');
  expect(view.props.onReloadNetwork).toHaveBeenCalledTimes(1);
  expect(api).toHaveBeenCalledTimes(1); assertReadOnly();
});

it('reports an explicit reload failure without creating or recomputing any plan', async () => {
  vi.mocked(api).mockRejectedValueOnce(Object.assign(new Error('Raw conflict'), { status: 409 }));
  mount({ onReloadNetwork: vi.fn().mockRejectedValue(new Error('Unavailable')) });
  await screen.findByRole('alert'); await click('Reload current plan');
  expect(screen.getByRole('alert')).toHaveTextContent(/could not be reloaded/);
  expect(api).toHaveBeenCalledTimes(1); assertReadOnly();
});

it('labels captured results stale after a network revision changes and keeps their export captured', async () => {
  const view = mount(); await settled();
  view.rerender(<DeliveryOutlook {...view.props} network={{ ...network, revision: 4 }} />);
  expect(screen.getByRole('status')).toHaveTextContent(/network changed.*older estimate/i);
  expect(api).toHaveBeenCalledTimes(1);
  await click('Export outlook JSON');
  expect((vi.mocked(downloadCaptured).mock.calls[0][1] as any).network_revision).toBe(3);
  const pending = deferred<any>(); vi.mocked(api).mockReturnValueOnce(pending.promise);
  await click('Check current inputs');
  expect(api).toHaveBeenLastCalledWith('/delivery-outlook', { expected_network_revision: 4, added_delay_minutes: 0, ambient_temperature_c: 30, fault_truck_id: null });
  await act(async () => { pending.reject(Object.assign(new Error('Unit-test refresh conflict'), { status: 409 })); });
  expect(screen.getByRole('alert')).toHaveTextContent(/plan changed/);
  assertReadOnly();
});

it('discards an in-flight result captured before a revision change', async () => {
  const pending = deferred<any>(); vi.mocked(api).mockReturnValueOnce(pending.promise);
  const view = mount();
  view.rerender(<DeliveryOutlook {...view.props} network={{ ...network, revision: 4 }} />);
  await act(async () => { pending.resolve(response()); });
  expect(screen.getByRole('alert')).toHaveTextContent(/plan changed while this estimate was running/i);
  expect(screen.queryByRole('button', { name: 'Export outlook JSON' })).not.toBeInTheDocument();
  expect(screen.queryByText(/The allocation selects/)).not.toBeInTheDocument();
  expect(api).toHaveBeenCalledTimes(1); assertReadOnly();
});

it('does not display a result that resolves after the outlook has been unmounted', async () => {
  const pending = deferred<any>(); vi.mocked(api).mockReturnValueOnce(pending.promise);
  const view = mount(); view.unmount();
  await act(async () => { pending.resolve(response()); });
  expect(screen.queryByRole('button', { name: 'Export outlook JSON' })).not.toBeInTheDocument();
  expect(view.props.onInspectShipment).not.toHaveBeenCalled();
  expect(api).toHaveBeenCalledTimes(1);
});
