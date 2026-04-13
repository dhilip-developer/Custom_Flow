cat > /root/custom_api/try_customs/static/app.js << 'EOF'
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('verifyForm');
    const inputSection = document.getElementById('inputSection');
    const resultsSection = document.getElementById('resultsSection');
    const submitBtn = document.getElementById('submitBtn');
    const clearBtn = document.getElementById('clearBtn');
    const newVerificationBtn = document.getElementById('newVerificationBtn');
    const errorBox = document.getElementById('errorBox');
    
    clearBtn.addEventListener('click', () => {
        form.reset();
        errorBox.classList.add('hidden');
    });

    newVerificationBtn.addEventListener('click', () => {
        resultsSection.classList.add('hidden');
        inputSection.classList.remove('hidden');
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorBox.classList.add('hidden');
        
        const originalBtnText = submitBtn.innerHTML;
        submitBtn.innerHTML = 'Verifying...';
        submitBtn.disabled = true;

        const formData = new FormData();
        ['bill_of_lading', 'invoice', 'packing_list', 'freight_certificate', 'insurance_certificate'].forEach(id => {
            const val = document.getElementById(id).value.trim();
            if (val) formData.append(id, val);
        });

        try {
            const API_BASE = `http://${window.location.hostname}:30494`;
            const response = await fetch(`${API_BASE}/cross-verify`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                let errorMsg = data.detail || 'An error occurred during verification.';
                if (typeof errorMsg !== 'string') {
                    try {
                        errorMsg = data.detail[0].msg;
                    } catch(e) {}
                }
                throw new Error(errorMsg);
            }

            renderResults(data);
            
            inputSection.classList.add('hidden');
            resultsSection.classList.remove('hidden');

        } catch (err) {
            errorBox.textContent = err.message;
            errorBox.classList.remove('hidden');
        } finally {
            submitBtn.innerHTML = originalBtnText;
            submitBtn.disabled = false;
        }
    });

    function renderResults(data) {
        const docChipsContainer = document.getElementById('docChips');
        docChipsContainer.innerHTML = '';
        data.documents_provided.forEach(doc => {
            const d = doc.replace(' (BOL)', '').replace(' Certificate', ' Cert');
            const chip = document.createElement('span');
            chip.className = 'doc-chip';
            chip.textContent = d;
            docChipsContainer.appendChild(chip);
        });

        const mismatchCount = data.mismatched_fields ? data.mismatched_fields.length : 0;
        const banner = document.getElementById('verdictBanner');
        const bannerText = document.getElementById('mismatchCountText');
        
        if (mismatchCount > 0) {
            banner.className = 'verdict-banner error';
            banner.innerHTML = `<svg viewBox="0 0 24 24" class="verdict-icon"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                                <span>${mismatchCount} mismatch(es) found</span>`;
        } else {
            banner.className = 'verdict-banner success';
            banner.innerHTML = `<svg viewBox="0 0 24 24" class="verdict-icon"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                                <span>All fields match perfectly</span>`;
        }

        const tbody = document.getElementById('resultsTableBody');
        tbody.innerHTML = '';
        
        const allComparisons = [
            ...(data.mismatched_fields || []),
            ...(data.matched_fields || [])
        ];

        if(allComparisons.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 2rem;">No comparisons could be made with the provided data.</td></tr>';
            return;
        }

        allComparisons.forEach(comp => {
            const tr = document.createElement('tr');
            
            const isMismatch = comp.status === 'MISMATCH';
            tr.className = isMismatch ? 'mismatch' : 'match';

            const docs = comp.documents_compared;
            const doc1 = docs[0];
            const doc2 = docs[1];

            let shortField = comp.field_name.split('—')[0].trim();
            const acronym1 = getAcronym(doc1);
            const acronym2 = getAcronym(doc2);
            shortField = `${shortField} (${acronym1}↔${acronym2})`;

            const source1Val = comp.values[doc1] || '—';
            const source2Val = comp.values[doc2] || '—';

            const statusHtml = isMismatch 
                ? '<span class="status-chip mismatch">X Mismatch</span>'
                : '<span class="status-chip match">✓ Match</span>';

            tr.innerHTML = `
                <td>
                    <div class="field-name">${shortField}</div>
                </td>
                <td>
                    <div class="source-block">
                        <span class="source-doc">${doc1.replace(' (BOL)', '')}</span>
                        <span class="source-val">${source1Val}</span>
                    </div>
                </td>
                <td>
                    <div class="source-block">
                        <span class="source-doc">${doc2.replace(' (BOL)', '')}</span>
                        <span class="source-val">${source2Val}</span>
                    </div>
                </td>
                <td>
                    ${statusHtml}
                </td>
            `;
            tbody.appendChild(tr);
            
            if(isMismatch && comp.discrepancy_note) {
                 const noteTr = document.createElement('tr');
                 noteTr.className = 'mismatch';
                 noteTr.innerHTML = `
                    <td colspan="4" style="padding-top: 0; padding-bottom: 1.5rem;">
                        <div style="font-size: 0.85rem; color: #991b1b; display: flex; gap: 0.5rem; align-items: flex-start;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-top:2px; flex-shrink:0;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                            <span>${comp.discrepancy_note}</span>
                        </div>
                    </td>
                 `;
                 tr.style.borderBottom = 'none';
                 tr.querySelector('td').style.borderBottom = 'none';
                 const tds = tr.querySelectorAll('td');
                 tds.forEach(td => td.style.borderBottom = 'none');
                 
                 tbody.appendChild(noteTr);
            }
        });
    }

    function getAcronym(docName) {
        if (docName.includes('Bill of Lading') || docName.includes('BOL')) return 'BL';
        if (docName.includes('Invoice')) return 'INV';
        if (docName.includes('Packing List')) return 'PL';
        if (docName.includes('Freight Certificate')) return 'FC';
        if (docName.includes('Insurance')) return 'INS';
        return docName.substring(0, 3).toUpperCase();
    }
});
EOF
