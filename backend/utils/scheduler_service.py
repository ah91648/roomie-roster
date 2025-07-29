import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import atexit

class SchedulerService:
    """Handles scheduled tasks for the RoomieRoster application."""
    
    def __init__(self, assignment_logic=None):
        self.assignment_logic = assignment_logic
        self.scheduler = None
        self.logger = logging.getLogger(__name__)
        
    def init_scheduler(self):
        """Initialize and start the APScheduler."""
        if self.scheduler is not None:
            return
            
        self.scheduler = BackgroundScheduler()
        
        # Add event listeners for logging
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
        
        # Schedule automatic cycle reset every Sunday at 11:59 PM
        self.scheduler.add_job(
            func=self._automatic_cycle_reset,
            trigger='cron',
            day_of_week='sun',
            hour=23,
            minute=59,
            id='weekly_cycle_reset',
            name='Weekly Cycle Reset',
            replace_existing=True,
            misfire_grace_time=300  # Allow up to 5 minutes grace period
        )
        
        # Start the scheduler
        self.scheduler.start()
        self.logger.info("Scheduler started with weekly cycle reset job")
        
        # Ensure the scheduler shuts down when the application exits
        atexit.register(self.shutdown)
        
    def _automatic_cycle_reset(self):
        """Perform automatic cycle reset."""
        try:
            self.logger.info("Starting automatic weekly cycle reset")
            
            if self.assignment_logic is None:
                self.logger.error("Assignment logic not available for automatic reset")
                return
                
            # Reset cycle points
            self.assignment_logic.reset_cycle_points()
            
            # Clear current assignments to force fresh assignment on next trigger
            self.assignment_logic.data_handler.save_current_assignments([])
            
            # Update last run date to mark the reset
            current_time = datetime.now()
            self.assignment_logic.data_handler.update_last_run_date(current_time.isoformat())
            
            self.logger.info(f"Automatic cycle reset completed successfully at {current_time}")
            
        except Exception as e:
            self.logger.error(f"Error during automatic cycle reset: {e}", exc_info=True)
            
    def _job_executed(self, event):
        """Log successful job execution."""
        self.logger.info(f"Job '{event.job_id}' executed successfully")
        
    def _job_error(self, event):
        """Log job execution errors."""
        self.logger.error(f"Job '{event.job_id}' crashed: {event.exception}")
        
    def manual_cycle_reset(self):
        """Perform manual cycle reset (for API endpoint)."""
        try:
            self.logger.info("Starting manual cycle reset")
            
            if self.assignment_logic is None:
                raise Exception("Assignment logic not available")
                
            # Reset cycle points
            self.assignment_logic.reset_cycle_points()
            
            # Update last run date
            current_time = datetime.now()
            self.assignment_logic.data_handler.update_last_run_date(current_time.isoformat())
            
            self.logger.info(f"Manual cycle reset completed successfully at {current_time}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during manual cycle reset: {e}", exc_info=True)
            raise
            
    def get_scheduler_status(self):
        """Get information about the scheduler and its jobs."""
        if self.scheduler is None:
            return {"status": "not_initialized"}
            
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
            
        return {
            "status": "running" if self.scheduler.running else "stopped",
            "jobs": jobs
        }
        
    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        if self.scheduler is not None and self.scheduler.running:
            self.logger.info("Shutting down scheduler")
            self.scheduler.shutdown()
            self.scheduler = None