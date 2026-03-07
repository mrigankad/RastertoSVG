#!/usr/bin/env python
"""Example: Python API client for the converter service."""

import argparse
import sys
import time
from pathlib import Path

import requests


class RasterToSVGClient:
    """Client for the Raster to SVG API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"

    def upload(self, file_path: str) -> dict:
        """Upload an image file."""
        with open(file_path, 'rb') as f:
            response = requests.post(
                f"{self.api_base}/upload",
                files={'file': f}
            )
        
        response.raise_for_status()
        return response.json()

    def convert(
        self,
        file_id: str,
        image_type: str = "auto",
        quality_mode: str = "standard",
        color_palette: int = 32,
        denoise_strength: str = "medium",
    ) -> dict:
        """Start a conversion job."""
        data = {
            'file_id': file_id,
            'image_type': image_type,
            'quality_mode': quality_mode,
            'color_palette': color_palette,
            'denoise_strength': denoise_strength,
        }
        
        response = requests.post(
            f"{self.api_base}/convert",
            data=data
        )
        
        response.raise_for_status()
        return response.json()

    def get_status(self, job_id: str) -> dict:
        """Get job status."""
        response = requests.get(f"{self.api_base}/status/{job_id}")
        response.raise_for_status()
        return response.json()

    def download_result(self, job_id: str, output_path: str):
        """Download conversion result."""
        response = requests.get(f"{self.api_base}/result/{job_id}")
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)

    def convert_and_wait(
        self,
        file_path: str,
        output_path: str = None,
        image_type: str = "auto",
        quality_mode: str = "standard",
        poll_interval: float = 1.0,
    ) -> dict:
        """
        Upload, convert, and wait for completion.
        
        Returns the final job status.
        """
        # Generate output path if not provided
        if output_path is None:
            input_path = Path(file_path)
            output_path = input_path.with_suffix('.svg')

        print(f"Uploading: {file_path}")
        upload_result = self.upload(file_path)
        file_id = upload_result['file_id']
        print(f"  Uploaded as: {file_id}")

        print(f"Starting conversion (quality: {quality_mode})")
        convert_result = self.convert(
            file_id=file_id,
            image_type=image_type,
            quality_mode=quality_mode,
        )
        job_id = convert_result['job_id']
        print(f"  Job ID: {job_id}")

        # Poll for completion
        print("Waiting for completion...")
        while True:
            status = self.get_status(job_id)
            progress = status.get('progress', 0)
            status_text = status['status']
            
            print(f"  {status_text}: {progress*100:.0f}%", end='\r')
            
            if status['status'] == 'completed':
                print(f"\n  Completed in {status.get('processing_time', 0):.2f}s")
                break
            elif status['status'] == 'failed':
                print(f"\n  Failed: {status.get('error', 'Unknown error')}")
                raise RuntimeError(f"Conversion failed: {status.get('error')}")
            
            time.sleep(poll_interval)

        # Download result
        print(f"Downloading result to: {output_path}")
        self.download_result(job_id, str(output_path))
        print("  Done!")

        return status

    def batch_convert(
        self,
        file_paths: list,
        quality_mode: str = "standard",
    ) -> dict:
        """Convert multiple files."""
        # Upload all files
        file_ids = []
        for file_path in file_paths:
            print(f"Uploading: {file_path}")
            result = self.upload(file_path)
            file_ids.append(result['file_id'])

        # Start batch conversion
        print(f"\nStarting batch conversion of {len(file_ids)} files")
        response = requests.post(
            f"{self.api_base}/batch",
            json={
                'file_ids': file_ids,
                'options': {
                    'image_type': 'auto',
                    'quality_mode': quality_mode,
                }
            }
        )
        response.raise_for_status()
        
        return response.json()

    def list_jobs(self, status: str = None, limit: int = 50) -> list:
        """List conversion jobs."""
        params = {'limit': limit}
        if status:
            params['status'] = status
        
        response = requests.get(f"{self.api_base}/jobs", params=params)
        response.raise_for_status()
        
        return response.json()

    def get_storage_stats(self) -> dict:
        """Get storage statistics."""
        response = requests.get(f"{self.api_base}/storage/stats")
        response.raise_for_status()
        return response.json()

    def get_queue_stats(self) -> dict:
        """Get queue statistics."""
        response = requests.get(f"{self.api_base}/queue/stats")
        response.raise_for_status()
        return response.json()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Raster to SVG API Client')
    parser.add_argument('--url', default='http://localhost:8000', help='API base URL')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert an image')
    convert_parser.add_argument('input', help='Input image path')
    convert_parser.add_argument('-o', '--output', help='Output SVG path')
    convert_parser.add_argument('-q', '--quality', default='standard',
                               choices=['fast', 'standard', 'high'],
                               help='Quality mode')
    convert_parser.add_argument('-t', '--type', default='auto',
                               choices=['auto', 'color', 'monochrome'],
                               help='Image type')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Batch convert images')
    batch_parser.add_argument('inputs', nargs='+', help='Input image paths')
    batch_parser.add_argument('-q', '--quality', default='standard',
                             choices=['fast', 'standard', 'high'],
                             help='Quality mode')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List jobs')
    list_parser.add_argument('-s', '--status', help='Filter by status')
    list_parser.add_argument('-l', '--limit', type=int, default=50, help='Max results')
    
    # Stats command
    subparsers.add_parser('stats', help='Show storage stats')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)

    client = RasterToSVGClient(args.url)

    try:
        if args.command == 'convert':
            client.convert_and_wait(
                args.input,
                args.output,
                image_type=args.type,
                quality_mode=args.quality,
            )

        elif args.command == 'batch':
            result = client.batch_convert(args.inputs, args.quality)
            print(f"Batch ID: {result['batch_id']}")
            print(f"Jobs: {result['total']}")
            for job_id in result['job_ids']:
                print(f"  - {job_id}")

        elif args.command == 'list':
            result = client.list_jobs(status=args.status, limit=args.limit)
            print(f"Jobs (showing {len(result['jobs'])} of {result['count']}):")
            for job in result['jobs']:
                print(f"  {job['job_id']}: {job['status']} ({job.get('progress', 0)*100:.0f}%)")

        elif args.command == 'stats':
            storage = client.get_storage_stats()
            queue = client.get_queue_stats()
            
            print("Storage Statistics:")
            print(f"  Uploads: {storage['uploads']['count']} files ({storage['uploads']['size_mb']:.1f} MB)")
            print(f"  Results: {storage['results']['count']} files ({storage['results']['size_mb']:.1f} MB)")
            print(f"  Total: {storage['total_size_mb']:.1f} MB")
            
            print("\nQueue Statistics:")
            print(f"  Pending: {queue['pending']}")
            print(f"  Processing: {queue['processing']}")
            print(f"  Completed: {queue['completed']}")
            print(f"  Failed: {queue['failed']}")

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to API at {args.url}")
        print("Make sure the server is running.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
