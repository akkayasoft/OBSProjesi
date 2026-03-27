// OBS - Genel JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Silme onay modalı
    document.querySelectorAll('[data-confirm]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm || 'Bu işlemi gerçekleştirmek istediğinizden emin misiniz?')) {
                e.preventDefault();
            }
        });
    });

    // Flash mesajlarını otomatik kapat
    document.querySelectorAll('.alert-dismissible').forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Para formatı
function formatCurrency(amount) {
    return new Intl.NumberFormat('tr-TR', {
        style: 'currency',
        currency: 'TRY'
    }).format(amount);
}
