import argparse
import os
import json
import shutil

def upload_file(file_path, target):
    """模拟文件上传"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found")
    print(f"Uploading {file_path} to {target}...")

def upload_all_files(target):
    """上传所有文件的检查清单"""
    checklist = [
        {"path": "block_variant_description.txt", "description": "Project description (from block + variant)"},
        {"path": "video_documentary.mp4", "description": "Video documentary (from #1)"},
        {"path": "project_images.zip", "description": "Project images (from #2)"},
        {"path": "portrait_photo.jpg", "description": "Portrait photo (from #3)"},
        {"path": "profile_bio.txt", "description": "Bio (from profile)"},
        {"path": "work_samples_urls.json", "description": "Work samples (8 URLs from profile)"},
        {"path": "additional_documents.zip", "description": "Additional documents (optional, see #7)"},
        {"path": "materials/resumes/multimedia-specialist.pdf", "description": "Resume"}
    ]
    for item in checklist:
        print(f"Preparing to upload: {item['description']}")
        upload_file(item['path'], target)

def main():
    parser = argparse.ArgumentParser(description='Submit files to the STARTS Prize portal.')
    parser.add_argument('--target', required=True, help='The target portal for submission (e.g., starts-prize)')
    parser.add_argument('--record', action='store_true', help='Record submission action')
    args = parser.parse_args()
    upload_all_files(args.target)
    if args.record:
        print("Recording submission to a log file.")
        with open("submission_log.json", "w") as log_file:
            log_data = {
                "submission_target": args.target,
                "status": "completed",
                "files_uploaded": [
                    "block_variant_description.txt",
                    "video_documentary.mp4",
                    "project_images.zip",
                    "portrait_photo.jpg",
                    "profile_bio.txt",
                    "work_samples_urls.json",
                    "additional_documents.zip",
                    "materials/resumes/multimedia-specialist.pdf"
                ]
            }
            json.dump(log_data, log_file, indent=4)
if __name__ == '__main__':
    main()