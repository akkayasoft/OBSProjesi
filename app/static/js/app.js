// OBS - Genel JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // --- Sidebar drawer (yalnizca mobil/tablet — desktop'ta kalici) ---
    var sidebar = document.getElementById('sidebar');
    var overlay = document.getElementById('sidebarOverlay');
    var toggle = document.getElementById('sidebarToggle');
    var body = document.body;
    var DESKTOP_BREAKPOINT = 992;

    function isMobile() {
        return window.innerWidth < DESKTOP_BREAKPOINT;
    }

    function openSidebar() {
        if (sidebar) sidebar.classList.add('show');
        if (overlay) overlay.classList.add('show');
        body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('show');
        if (overlay) overlay.classList.remove('show');
        body.style.overflow = '';
    }

    function toggleSidebar(e) {
        if (e) { e.preventDefault(); e.stopPropagation(); }
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

    // Mobilde sidebar icindeki linklere tiklaninca otomatik kapat
    if (sidebar) {
        sidebar.querySelectorAll('a.sidebar-link:not(.has-children)').forEach(function(link) {
            link.addEventListener('click', function() {
                if (isMobile()) closeSidebar();
            });
        });
    }

    // Pencere genislerse mobile-show state'ini temizle
    window.addEventListener('resize', function() {
        if (!isMobile()) closeSidebar();
    });

    // --- Sidebar arama (live filter) ---
    var searchInput = document.getElementById('sidebarSearch');
    var searchClear = document.getElementById('sidebarSearchClear');
    var sidebarEmpty = document.getElementById('sidebarEmpty');

    function _normalize(s) {
        s = (s || '').toString().toLowerCase();
        return s.replace(/[ıİ]/g, 'i').replace(/[şŞ]/g, 's')
                .replace(/[ğĞ]/g, 'g').replace(/[üÜ]/g, 'u')
                .replace(/[öÖ]/g, 'o').replace(/[çÇ]/g, 'c');
    }

    function _matchesText(node, q) {
        // Section icindeki tum sidebar-link metnini topla
        var labels = node.querySelectorAll('.sidebar-link');
        for (var i = 0; i < labels.length; i++) {
            var t = _normalize(labels[i].textContent.trim());
            if (t.indexOf(q) !== -1) return true;
        }
        return false;
    }

    function applySidebarFilter() {
        if (!searchInput || !sidebar) return;
        var q = _normalize(searchInput.value.trim());
        var sections = sidebar.querySelectorAll('.sidebar-section');
        var visibleCount = 0;
        sections.forEach(function(sec) {
            if (!q) {
                sec.classList.remove('is-hidden');
                // Collapse'lari kullanicinin onceki state'ine birak
                visibleCount++;
                return;
            }
            if (_matchesText(sec, q)) {
                sec.classList.remove('is-hidden');
                // Eslesirse alt collapse'lari otomatik ac
                var collapse = sec.querySelector('.collapse');
                if (collapse && !collapse.classList.contains('show')) {
                    collapse.classList.add('show');
                }
                visibleCount++;
            } else {
                sec.classList.add('is-hidden');
            }
        });
        // "Sonuc yok" durumunu goster/gizle
        if (sidebarEmpty) {
            if (q && visibleCount === 0) {
                sidebarEmpty.classList.remove('d-none');
            } else {
                sidebarEmpty.classList.add('d-none');
            }
        }
        // Clear butonu
        if (searchClear) {
            if (q) {
                searchClear.classList.remove('d-none');
            } else {
                searchClear.classList.add('d-none');
            }
        }
    }

    if (searchInput) {
        searchInput.addEventListener('input', applySidebarFilter);
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                searchInput.value = '';
                applySidebarFilter();
                searchInput.blur();
            }
        });
    }
    if (searchClear) {
        searchClear.addEventListener('click', function() {
            if (searchInput) {
                searchInput.value = '';
                searchInput.focus();
                applySidebarFilter();
            }
        });
    }
    // Klavye kisayolu: '/' -> arama kutusuna odakla
    document.addEventListener('keydown', function(e) {
        if (e.key === '/' && document.activeElement &&
            document.activeElement.tagName !== 'INPUT' &&
            document.activeElement.tagName !== 'TEXTAREA' &&
            !document.activeElement.isContentEditable) {
            if (searchInput) {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
            }
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
        // Bazi mesajlar (orn. sifre sifirlama) kullaniciya kalmali
        if (alert.dataset.noAutoclose === '1') return;
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
