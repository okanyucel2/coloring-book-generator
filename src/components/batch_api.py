"""
Flask API endpoints for batch job management.
Integrates with GENESIS backend.
"""
from flask import Blueprint, request, jsonify
from coloring_book.batch_runner import BatchRunner, JobStatus

batch_bp = Blueprint('batch', __name__, url_prefix='/api/v1/batch')
batch_runner = BatchRunner()


@batch_bp.route('/generate', methods=['POST'])
def create_batch_job():
    """Create and start a new batch generation job"""
    try:
        data = request.get_json()
        
        job = batch_runner.create_job(
            name=data.get('job_name', 'Batch Job'),
            animal_count=data.get('animal_count', 5),
            animal_types=data.get('animal_types', []),
            page_size=data.get('page_size', 'A4'),
            use_ai=data.get('use_ai', True),
        )
        
        # Start processing
        batch_runner.start_job(job.id)
        
        return jsonify({
            'status': 'success',
            'job_id': job.id,
            'message': f'Batch job {job.id} started',
        }), 202
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
        }), 400


@batch_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """Get all batch jobs with current status"""
    try:
        jobs = batch_runner.get_jobs()
        
        return jsonify({
            'status': 'success',
            'jobs': [
                {
                    'id': job.id,
                    'name': job.name,
                    'status': job.status.value,
                    'total': job.total_items,
                    'current': job.completed_items,
                    'failed': job.failed_items,
                    'progress': job.progress,
                    'created_at': job.created_at,
                    'started_at': job.started_at,
                    'completed_at': job.completed_at,
                }
                for job in jobs
            ]
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
        }), 400


@batch_bp.route('/jobs/<job_id>', methods=['GET'])
def get_job_detail(job_id):
    """Get detailed info for a specific job"""
    try:
        job = batch_runner.get_job(job_id)
        
        if not job:
            return jsonify({
                'status': 'error',
                'message': 'Job not found',
            }), 404
        
        return jsonify({
            'status': 'success',
            'job': {
                'id': job.id,
                'name': job.name,
                'status': job.status.value,
                'total': job.total_items,
                'completed': job.completed_items,
                'failed': job.failed_items,
                'progress': job.progress,
                'config': job.config,
                'created_at': job.created_at,
                'started_at': job.started_at,
                'completed_at': job.completed_at,
                'error_message': job.error_message,
                'output_path': job.output_path,
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
        }), 400


@batch_bp.route('/jobs/<job_id>/pause', methods=['POST'])
def pause_job(job_id):
    """Pause a running batch job"""
    try:
        success = batch_runner.pause_job(job_id)
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': 'Failed to pause job',
            }), 400
        
        return jsonify({
            'status': 'success',
            'message': f'Job {job_id} paused',
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
        }), 400


@batch_bp.route('/jobs/<job_id>/resume', methods=['POST'])
def resume_job(job_id):
    """Resume a paused batch job"""
    try:
        success = batch_runner.resume_job(job_id)
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': 'Failed to resume job',
            }), 400
        
        return jsonify({
            'status': 'success',
            'message': f'Job {job_id} resumed',
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
        }), 400


@batch_bp.route('/jobs/<job_id>/delete', methods=['DELETE'])
def delete_job(job_id):
    """Delete a batch job and its outputs"""
    try:
        success = batch_runner.delete_job(job_id)
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': 'Job not found',
            }), 404
        
        return jsonify({
            'status': 'success',
            'message': f'Job {job_id} deleted',
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
        }), 400
