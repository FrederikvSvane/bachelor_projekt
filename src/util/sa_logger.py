import numpy as np
from typing import List, Optional
import json
from datetime import datetime
import os

from src.util.energy_funnel_visualizer import SearchState, EnergyFunnelVisualizer, extract_schedule_features


class SimulatedAnnealingLogger:
    """Logger for capturing search states during simulated annealing"""
    
    def __init__(self, log_every_n_iterations: int = 10):
        self.states: List[SearchState] = []
        self.log_every_n_iterations = log_every_n_iterations
        self.iteration_count = 0
        self.best_score = float('inf')
        
    def log_state(self, 
                  schedule,
                  score: float,
                  temperature: float,
                  move_type: str,
                  is_accepted: bool,
                  event_type: Optional[str] = None):
        """Log a search state"""
        
        self.iteration_count += 1
        
        # Only log every n iterations to avoid too much data
        if self.iteration_count % self.log_every_n_iterations != 0:
            # But always log special events and best solutions
            if event_type is None and score >= self.best_score:
                return
                
        is_best = score < self.best_score
        if is_best:
            self.best_score = score
            
        # Extract features from schedule
        features = extract_schedule_features(schedule)
        
        state = SearchState(
            iteration=self.iteration_count,
            score=score,
            temperature=temperature,
            schedule_features=features,
            move_type=move_type,
            is_accepted=is_accepted,
            is_best=is_best,
            event_type=event_type
        )
        
        self.states.append(state)
        
    def create_visualization(self, output_path: str = None):
        """Create the energy funnel visualization"""
        if not self.states:
            print("No states logged!")
            return None
            
        print(f"Creating visualization from {len(self.states)} logged states...")
        
        viz = EnergyFunnelVisualizer(self.states)
        
        if output_path:
            viz.save_html(output_path)
        else:
            # Default path with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = "/Users/frederik/projects/personal/bachelor_projekt/src/util/data_visualizer"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"energy_funnel_{timestamp}.html")
            viz.save_html(output_path)
            
        return viz
        
    def save_log(self, filepath: str):
        """Save the log data to a JSON file"""
        data = []
        for state in self.states:
            data.append({
                'iteration': state.iteration,
                'score': state.score,
                'temperature': state.temperature,
                'features': state.schedule_features.tolist(),
                'move_type': state.move_type,
                'is_accepted': state.is_accepted,
                'is_best': state.is_best,
                'event_type': state.event_type
            })
            
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            
    @staticmethod
    def load_log(filepath: str) -> 'SimulatedAnnealingLogger':
        """Load log data from a JSON file"""
        logger = SimulatedAnnealingLogger()
        
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        for item in data:
            state = SearchState(
                iteration=item['iteration'],
                score=item['score'],
                temperature=item['temperature'],
                schedule_features=np.array(item['features']),
                move_type=item['move_type'],
                is_accepted=item['is_accepted'],
                is_best=item['is_best'],
                event_type=item.get('event_type')
            )
            logger.states.append(state)
            
        return logger