    // Handle BOM tree expansion
    document.querySelectorAll('.bom-expand-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const target = this.dataset.target;
            const icon = this.querySelector('i');
            
            document.querySelectorAll(target).forEach(el => {
                el.classList.toggle('d-none');
            });
            
            if (icon.classList.contains('fa-plus')) {
                icon.classList.remove('fa-plus');
                icon.classList.add('fa-minus');
            } else {
                icon.classList.remove('fa-minus');
                icon.classList.add('fa-plus');
            }
        });
    });
    
    // Handle select all checkbox
    const selectAllCheckbox = document.getElementById('select-all');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            document.querySelectorAll('.order-select').forEach(checkbox => {
                checkbox.checked = this.checked;
            });
        });
    }
