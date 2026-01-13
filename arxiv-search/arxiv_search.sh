#!/usr/bin/env bash
# arXiv Search - Bash implementation
# Searches the arXiv preprint repository for research papers.

set -euo pipefail

usage() {
    cat <<EOF
Usage: $(basename "$0") <query> [--max-papers N]

Search arXiv for research papers.

Arguments:
    query           Search query string
    --max-papers N  Maximum number of papers to retrieve (default: 10)

Examples:
    $(basename "$0") "transformer attention mechanism"
    $(basename "$0") "quantum computing" --max-papers 5
EOF
    exit 1
}

# Check dependencies
command -v curl >/dev/null 2>&1 || { echo "Error: curl is required"; exit 1; }

# Parse arguments
MAX_PAPERS=10
QUERY=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --max-papers)
            MAX_PAPERS="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            if [[ -z "$QUERY" ]]; then
                QUERY="$1"
            else
                QUERY="$QUERY $1"
            fi
            shift
            ;;
    esac
done

[[ -z "$QUERY" ]] && usage

# URL-encode the query
encode_query() {
    local string="$1"
    local encoded=""
    local i char
    for (( i=0; i<${#string}; i++ )); do
        char="${string:i:1}"
        case "$char" in
            [a-zA-Z0-9.~_-]) encoded+="$char" ;;
            ' ') encoded+='+' ;;
            *) encoded+=$(printf '%%%02X' "'$char") ;;
        esac
    done
    echo "$encoded"
}

ENCODED_QUERY=$(encode_query "$QUERY")
API_URL="https://export.arxiv.org/api/query?search_query=all:${ENCODED_QUERY}&start=0&max_results=${MAX_PAPERS}&sortBy=relevance&sortOrder=descending"

# Fetch and parse results
response=$(curl -s "$API_URL")

# Check for valid response
if [[ -z "$response" ]]; then
    echo "Error: No response from arXiv API"
    exit 1
fi

# Extract titles and summaries using awk (compatible with macOS and GNU awk)
parse_results() {
    echo "$response" | awk '
    BEGIN { RS="</entry>"; count=0 }
    /<entry>/ {
        # Get content after <entry> tag to skip feed-level title
        entry_start = index($0, "<entry>")
        if (entry_start == 0) next
        entry_content = substr($0, entry_start + 7)

        # Extract title from entry content
        title = ""
        if (match(entry_content, /<title>/)) {
            rest = substr(entry_content, RSTART + 7)
            if (match(rest, /<\/title>/)) {
                title = substr(rest, 1, RSTART - 1)
            }
        }

        # Extract summary from entry content
        summary = ""
        if (match(entry_content, /<summary>/)) {
            rest = substr(entry_content, RSTART + 9)
            if (match(rest, /<\/summary>/)) {
                summary = substr(rest, 1, RSTART - 1)
            }
        }

        # Clean whitespace
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", title)
        gsub(/[[:space:]]+/, " ", summary)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", summary)

        # Only print if we have both title and summary
        if (title != "" && summary != "") {
            if (count > 0) print ""
            print "Title: " title
            print "Summary: " summary
            count++
        }
    }
    END {
        if (count == 0) print "No papers found on arXiv."
    }
    '
}

parse_results
