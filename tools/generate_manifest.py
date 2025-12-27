import os
import json
import sys

def generate_manifest(base_dir, public_url_prefix):
    files_list = []
    
    # Categories to scan
    categories = ['start', 'end', 'interval', 'resume', 'exit']
    
    # Walk through the directory
    for root, dirs, files in os.walk(base_dir):
        for name in files:
            if not name.lower().endswith(('.mp3', '.wav', '.ogg')):
                continue
                
            # Get relative path from base_dir
            rel_path = os.path.relpath(os.path.join(root, name), base_dir)
            # Normalize path separators to forward slash for URLs
            rel_path_web = rel_path.replace(os.sep, '/')
            
            # Determine category, season, tag from path structure
            # Expected structures:
            # 1. category/file.mp3
            # 2. category/season/file.mp3
            # 3. category/tags/tagname/file.mp3
            # 4. holidays/holiday_name/type/file.mp3 (New)
            
            parts = rel_path_web.split('/')
            category = 'start' # default fallback
            season = None
            tag = None
            holiday = None
            holiday_type = None
            
            # Check if the first folder is a valid category
            if len(parts) > 1:
                top_folder = parts[0]
                
                if top_folder == 'holidays':
                    # case: holidays/holiday_name/type/file.mp3
                    category = 'holiday'
                    if len(parts) > 2:
                        holiday = parts[1]
                        if len(parts) > 3:
                            holiday_type = parts[2]
                        else:
                            # Fallback if no type specified, though expected
                            holiday_type = 'common'
                
                elif top_folder in categories:
                    category = top_folder
                    
                    # Check for subfolders
                    if len(parts) > 2: 
                        # case: category/subdir/file.mp3
                        subdir = parts[1]
                        
                        if subdir == 'tags':
                            # case: category/tags/tagname/file.mp3
                            if len(parts) > 3:
                                tag = parts[2]
                        else:
                            # case: category/season/file.mp3
                            season = subdir
            
            # Construct absolute URL
            full_url = public_url_prefix.rstrip('/') + '/' + rel_path_web
            
            item = {
                "url": full_url,
                "category": category
            }
            if season:
                item["season"] = season
            if tag:
                item["tag"] = tag
            if holiday:
                item["holiday"] = holiday
            if holiday_type:
                item["type"] = holiday_type
                
            files_list.append(item)
            
    return {"files": files_list}

if __name__ == "__main__":
    print("=== Pomodoro Sound Manifest Generator ===")
    print("This tool generates a manifest.json file for your cloud sounds.")
    print("Steps:")
    print("1. Organize your sounds in folders (e.g. sounds/start, sounds/end)")
    print("2. Upload them to your web server")
    print("3. Use this tool to generate manifest.json")
    print("---------------------------------------")
    
    # Default to 'sounds' in current directory if exists, else current directory
    default_dir = "./sounds" if os.path.exists("./sounds") else "."
    
    target_dir = input(f"Enter local path to scanned folder (default: {default_dir}): ").strip()
    if not target_dir:
        target_dir = default_dir
        
    if not os.path.exists(target_dir):
        print(f"Error: Directory '{target_dir}' not found.")
        sys.exit(1)
        
    url_prefix = input("Enter the public URL prefix (e.g. https://mysite.com/pomodoro/sounds): ").strip()
    if not url_prefix:
        print("Error: URL prefix is required.")
        sys.exit(1)
        
    print(f"Scanning {target_dir}...")
    manifest = generate_manifest(target_dir, url_prefix)
    
    output_path = os.path.join(target_dir, "manifest.json")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4)
        print(f"\n[SUCCESS] Generated {output_path}")
        print(f"Contains {len(manifest['files'])} files.")
        print("\nNow upload 'manifest.json' to your server and set the URL in the app settings!")
    except Exception as e:
        print(f"\n[ERROR] Failed to write manifest: {e}")
