import sys
import json

def main():
    # Only mock 'gh issue list' and 'gh repo view'
    args = sys.argv[1:]
    
    if args[:2] == ["repo", "view"]:
        print(json.dumps({"nameWithOwner": "mock-owner/mock-repo"}))
        sys.exit(0)
        
    if args[:2] == ["issue", "list"]:
        # Mocking issue list
        issues = [
            {
                "number": 1,
                "title": "M1-01 Mock Issue 1",
                "body": "Mock body 1",
                "url": "https://example.com/1"
            },
            {
                "number": 2,
                "title": "M1-02 Mock Issue 2",
                "body": "Mock body 2",
                "url": "https://example.com/2"
            }
        ]
        print(json.dumps(issues))
        sys.exit(0)
        
    # Just print the arguments for any other gh commands (like close milestone)
    print(f"[mock-gh] Executed gh command with args: {args}")
    sys.exit(0)

if __name__ == "__main__":
    main()