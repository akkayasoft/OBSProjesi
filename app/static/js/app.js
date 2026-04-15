// OBS - Genel JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // --- Sidebar toggle (mobil / tablet) ---
    var sidebar = document.getElementById('sidebar');
    var overlay = document.getElementById('sidebarOverlay');
    var toggle = document.getElementById('sidebarToggle');

    function openSidebar() {
        if (sidebar) sidebar.classList.add('show');
        if (overlay) overlay.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('show');
        if (overlay) overlay.classList.remove('show');
        document.body.style.overflow = '';
    }

    function toggleSidebar(e) {
        e.preventDefault();
        e.stopPropagation();
        if (sidebar && sidebar.classList.contains('show')) {
            closeSidebar();
        } else {
            openSidebar();
        }
    }

    if (toggle) {
        toggle.addEventListener('click', toggleSidebar);
        toggle.addEventListener('touchend', function(e) {
            e.preventDefault();
            toggleSidebar(e);
        }, { passive: false });
    }

    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
        overlay.addEventListener('touchend', function(e) {
            e.preventDefault();
            closeSidebar();
        }, { passive: false });
    }

    // Sidebar icindeki linklere tiklaninca kapat (mobilde)
    if (sidebar) {
        sidebar.querySelectorAll('a.sidebar-link:not(.has-children)').forEach(function(link) {
            link.addEventListener('click', function() {
                if (window.innerWidth < 992) {
                    closeSidebar();
                }
            });
        });
    }

    // Ekran genisleyince sidebar state'ini temizle
    window.addEventListener('resize', function() {
        if (window.innerWidth >= 992) {
            closeSidebar();
        }
    });

    // --- Silme onay modali ---
    document.querySelectorAll('[data-confirm]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm || 'Bu işlemi gerçekleştirmek istediğinizden emin misiniz?')) {
                e.preventDefault();
            }
        });
    });

    // --- Flash mesajlarini otomatik kapat ---
    document.querySelectorAll('.alert-dismissible').forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Para formati
function formatCurrency(amount) {
    return new Intl.NumberFormat('tr-TR', {
        style: 'currency',
        currency: 'TRY'
    }).format(amount);
}
