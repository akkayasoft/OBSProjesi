// OBS - Genel JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // --- Sidebar toggle ---
    var sidebar = document.getElementById('sidebar');
    var overlay = document.getElementById('sidebarOverlay');
    var toggle = document.getElementById('sidebarToggle');
    var body = document.body;
    var DESKTOP_BREAKPOINT = 992;
    var COLLAPSED_KEY = 'obs:sidebar:collapsed';

    function isDesktop() {
        return window.innerWidth >= DESKTOP_BREAKPOINT;
    }

    // --- Mobil: overlay + slide-in ---
    function openMobileSidebar() {
        if (sidebar) sidebar.classList.add('show');
        if (overlay) overlay.classList.add('show');
        body.style.overflow = 'hidden';
    }

    function closeMobileSidebar() {
        if (sidebar) sidebar.classList.remove('show');
        if (overlay) overlay.classList.remove('show');
        body.style.overflow = '';
    }

    // --- Desktop: collapse/expand (margin sifirlanir, sidebar kayar) ---
    function applyDesktopCollapsed(collapsed) {
        if (collapsed) {
            body.classList.add('sidebar-collapsed');
        } else {
            body.classList.remove('sidebar-collapsed');
        }
    }

    function toggleDesktopSidebar() {
        var collapsed = !body.classList.contains('sidebar-collapsed');
        applyDesktopCollapsed(collapsed);
        try {
            localStorage.setItem(COLLAPSED_KEY, collapsed ? '1' : '0');
        } catch (e) { /* private mode */ }
    }

    // Sayfa yuklenirken kaydedilmis durumu uygula (sadece desktop'ta)
    if (isDesktop()) {
        try {
            if (localStorage.getItem(COLLAPSED_KEY) === '1') {
                applyDesktopCollapsed(true);
            }
        } catch (e) { /* private mode */ }
    }

    function handleToggle(e) {
        if (e) { e.preventDefault(); e.stopPropagation(); }
        if (isDesktop()) {
            toggleDesktopSidebar();
        } else {
            if (sidebar && sidebar.classList.contains('show')) {
                closeMobileSidebar();
            } else {
                openMobileSidebar();
            }
        }
    }

    if (toggle) {
        toggle.addEventListener('click', handleToggle);
        toggle.addEventListener('touchend', function(e) {
            e.preventDefault();
            handleToggle(e);
        }, { passive: false });
    }

    if (overlay) {
        overlay.addEventListener('click', closeMobileSidebar);
        overlay.addEventListener('touchend', function(e) {
            e.preventDefault();
            closeMobileSidebar();
        }, { passive: false });
    }

    // Mobilde sidebar icindeki linklere tiklaninca kapat
    if (sidebar) {
        sidebar.querySelectorAll('a.sidebar-link:not(.has-children)').forEach(function(link) {
            link.addEventListener('click', function() {
                if (!isDesktop()) {
                    closeMobileSidebar();
                }
            });
        });
    }

    // Pencere boyutu degisince:
    // - Mobile→Desktop: mobile show'u temizle, kaydedilmis collapse durumunu uygula
    // - Desktop→Mobile: collapsed'i temizle (mobilde her zaman acilabilir)
    window.addEventListener('resize', function() {
        if (isDesktop()) {
            closeMobileSidebar();
            try {
                applyDesktopCollapsed(localStorage.getItem(COLLAPSED_KEY) === '1');
            } catch (e) { /* */ }
        } else {
            applyDesktopCollapsed(false);
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
