#!/usr/bin/env python3
"""
Web server wrapper for Cloud Run
Triggers scraping via HTTP endpoints
"""

from flask import Flask, request, jsonify, send_file
import subprocess
import os
import threading
import logging
import uuid
import json
import glob

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Track running jobs
running_jobs = {}
RESULTS_DIR = '/app/results'

def run_scraper(job_id, limit=None, breeds=None):
    """Run the Selenium-based scraper in background"""
    try:
        # Ensure results directory exists
        os.makedirs(RESULTS_DIR, exist_ok=True)
        
        cmd = ['python3', 'jobs/akc_selenium_scraper.py', '--cloud', '--headless', '--output-dir', RESULTS_DIR]
        
        if limit:
            cmd.extend(['--limit', str(limit)])
        elif breeds:
            cmd.extend(['--breeds'] + breeds)
        
        logger.info(f"Starting job {job_id}: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Find the output file
        output_file = None
        if result.returncode == 0:
            # Look for the generated JSON file
            json_files = glob.glob(os.path.join(RESULTS_DIR, f"akc_breeds_*.json"))
            if json_files:
                # Get the most recent file
                output_file = max(json_files, key=os.path.getctime)
        
        running_jobs[job_id] = {
            'status': 'completed',
            'output': result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout,
            'error': result.stderr if result.returncode != 0 else None,
            'return_code': result.returncode,
            'output_file': output_file,
            'results_count': 0
        }
        
        # Count results if file exists
        if output_file and os.path.exists(output_file):
            try:
                with open(output_file, 'r') as f:
                    data = json.load(f)
                    running_jobs[job_id]['results_count'] = len(data)
                    # Count successful extractions
                    successful = len([item for item in data if item.get('extraction_status') == 'success'])
                    running_jobs[job_id]['successful_extractions'] = successful
            except:
                pass
        
        logger.info(f"Job {job_id} completed with return code {result.returncode}")
        
    except Exception as e:
        running_jobs[job_id] = {
            'status': 'failed',
            'error': str(e)
        }
        logger.error(f"Job {job_id} failed: {e}")

@app.route('/')
def home():
    return jsonify({
        'service': 'AKC Breed Scraper (File-Based)',
        'status': 'ready',
        'endpoints': {
            'GET /': 'Service info',
            'GET /health': 'Health check',
            'POST /scrape': 'Start scraping job',
            'GET /status/<job_id>': 'Check job status',
            'GET /jobs': 'List all jobs',
            'GET /download/<job_id>': 'Download results file',
            'GET /files': 'List available result files'
        }
    })

@app.route('/health')
def health():
    """Health check for Cloud Run"""
    return 'OK', 200

@app.route('/scrape', methods=['POST'])
def scrape():
    """Start scraping job"""
    data = request.get_json() or {}
    
    # Generate job ID
    job_id = str(uuid.uuid4())[:8]
    
    # Start scraping in background
    running_jobs[job_id] = {'status': 'running'}
    
    thread = threading.Thread(
        target=run_scraper,
        args=(job_id, data.get('limit'), data.get('breeds'))
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'status': 'started',
        'message': f'Scraping job started. Check status at /status/{job_id}'
    })

@app.route('/status/<job_id>')
def status(job_id):
    """Check job status"""
    if job_id not in running_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(running_jobs[job_id])

@app.route('/jobs')
def list_jobs():
    """List all jobs"""
    jobs_summary = {}
    for job_id, job_data in running_jobs.items():
        jobs_summary[job_id] = {
            'status': job_data.get('status'),
            'return_code': job_data.get('return_code'),
            'results_count': job_data.get('results_count', 0),
            'successful_extractions': job_data.get('successful_extractions', 0),
            'has_output_file': bool(job_data.get('output_file'))
        }
    return jsonify(jobs_summary)

@app.route('/download/<job_id>')
def download_results(job_id):
    """Download results file for a job"""
    if job_id not in running_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job_data = running_jobs[job_id]
    output_file = job_data.get('output_file')
    
    if not output_file or not os.path.exists(output_file):
        return jsonify({'error': 'No output file available for this job'}), 404
    
    return send_file(
        output_file, 
        as_attachment=True, 
        download_name=f'akc_breeds_{job_id}.json',
        mimetype='application/json'
    )

@app.route('/files')
def list_files():
    """List all available result files"""
    if not os.path.exists(RESULTS_DIR):
        return jsonify({'files': []})
    
    files = []
    for filename in os.listdir(RESULTS_DIR):
        if filename.endswith('.json'):
            filepath = os.path.join(RESULTS_DIR, filename)
            stat = os.stat(filepath)
            files.append({
                'filename': filename,
                'size': stat.st_size,
                'modified': stat.st_mtime
            })
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: x['modified'], reverse=True)
    
    return jsonify({'files': files})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)