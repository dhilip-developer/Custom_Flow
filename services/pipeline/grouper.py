from typing import List, Dict


class DocumentGrouper:
    """
    V3 Grouper: Groups pages into logical document units.
    
    Handles:
    1. Consecutive pages of the same type -> single group
    2. "continuation" pages -> merge into the previous document group
    3. Skip "terms_and_conditions", "cover_letter", "skipped", "unknown"
    """

    SKIP_TYPES = {"terms_and_conditions", "cover_letter", "skipped", "unknown"}

    @staticmethod
    def group(pages: List[Dict]) -> List[Dict]:
        """
        Input: List of classified pages (with document_type from classifier).
        Output: List of document groups, each with type, page numbers, and buffers.
        """
        if not pages:
            return []

        groups: List[Dict] = []
        current_group = None

        for p in pages:
            doc_type = p.get("document_type", "unknown")

            # Skip junk pages entirely
            if doc_type in DocumentGrouper.SKIP_TYPES:
                continue

            # Check if this page is a forced new document (from heuristic hint)
            is_forced_split = p.get("is_new_document_hint", False)

            # "continuation" pages attach to the previous group (unless forced split)
            if doc_type == "continuation" and current_group and not is_forced_split:
                current_group["pages"].append(p["page_number"])
                current_group["buffers"].append(p["buffer"])
                continue

            # Same type as current group -> extend (unless forced split)
            if current_group and current_group["document_type"] == doc_type and not is_forced_split:
                current_group["pages"].append(p["page_number"])
                current_group["buffers"].append(p["buffer"])
            else:
                # New document type -> start new group
                if current_group:
                    groups.append(current_group)

                current_group = {
                    "document_type": doc_type,
                    "pages": [p["page_number"]],
                    "buffers": [p["buffer"]],
                }

        # Don't forget the last group
        if current_group:
            groups.append(current_group)

        print(f"[Grouper] {len(groups)} document groups formed from {len(pages)} pages")
        for g in groups:
            pg_range = f"{g['pages'][0]}-{g['pages'][-1]}" if len(g['pages']) > 1 else str(g['pages'][0])
            print(f"  → {g['document_type']} [{pg_range}] ({len(g['pages'])} pages)")

        return groups
