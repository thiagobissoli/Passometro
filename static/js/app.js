// Passômetro - Custom JavaScript

$(document).ready(function() {
    // Initialize tooltips
    $('[data-toggle="tooltip"]').tooltip();
    
    // Initialize popovers
    $('[data-toggle="popover"]').popover();
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
    
    // Real-time updates for critical items
    updateCriticalItems();
    
    // Initialize form validations
    initializeFormValidations();
    
    // Initialize timeline animations
    initializeTimelineAnimations();
});

// Update critical items every 30 seconds
function updateCriticalItems() {
    setInterval(function() {
        fetch('/api/pendencias/criticas')
            .then(response => response.json())
            .then(data => {
                updateCriticalCounters(data);
                updateCriticalAlerts(data);
            })
            .catch(error => {
                console.error('Erro ao atualizar dados críticos:', error);
            });
    }, 30000);
}

// Update critical counters
function updateCriticalCounters(data) {
    const criticalCount = data.filter(item => item.sla_restante < 60).length;
    
    // Update badge counts
    $('.badge-critical-count').text(criticalCount);
    
    // Update small box counters
    $('.small-box.bg-danger .inner h3').text(criticalCount);
    
    // Add pulse animation for critical items
    if (criticalCount > 0) {
        $('.small-box.bg-danger').addClass('pulse-critical');
    } else {
        $('.small-box.bg-danger').removeClass('pulse-critical');
    }
}

// Update critical alerts
function updateCriticalAlerts(data) {
    const criticalItems = data.filter(item => item.sla_restante < 60);
    
    if (criticalItems.length > 0) {
        showCriticalNotification(criticalItems);
    }
}

// Show critical notification
function showCriticalNotification(items) {
    // Check if browser supports notifications
    if (!("Notification" in window)) {
        return;
    }
    
    // Request permission if not granted
    if (Notification.permission !== "granted") {
        Notification.requestPermission();
        return;
    }
    
    // Show notification
    const notification = new Notification("Passômetro - Alertas Críticos", {
        body: `${items.length} pendência(s) crítica(s) vencendo SLA`,
        icon: "/static/images/logo.png",
        tag: "critical-alert"
    });
    
    // Auto close after 5 seconds
    setTimeout(() => {
        notification.close();
    }, 5000);
}

// Initialize form validations
function initializeFormValidations() {
    // SBAR form validation
    $('#sbar-form').on('submit', function(e) {
        const situacao = $('#situacao').val().trim();
        const background = $('#background').val().trim();
        const avaliacao = $('#avaliacao').val().trim();
        const recomendacao = $('#recomendacao').val().trim();
        
        if (!situacao || !background || !avaliacao || !recomendacao) {
            e.preventDefault();
            showAlert('Por favor, preencha todos os campos do SBAR', 'warning');
            return false;
        }
    });
    
    // I-PASS form validation
    $('#ipass-form').on('submit', function(e) {
        const severity = $('#illness_severity').val();
        const summary = $('#patient_summary').val().trim();
        const actions = $('#action_list').val().trim();
        const awareness = $('#situation_awareness').val().trim();
        
        if (!severity || !summary || !actions || !awareness) {
            e.preventDefault();
            showAlert('Por favor, preencha todos os campos do I-PASS', 'warning');
            return false;
        }
    });
    
    // Pendency form validation
    $('#pendency-form').on('submit', function(e) {
        const descricao = $('#descricao').val().trim();
        const responsavel = $('#responsavel_id').val();
        const prazo = $('#prazo').val();
        
        if (!descricao || !responsavel || !prazo) {
            e.preventDefault();
            showAlert('Por favor, preencha todos os campos obrigatórios', 'warning');
            return false;
        }
        
        // Validate deadline
        const deadline = new Date(prazo);
        const now = new Date();
        
        if (deadline <= now) {
            e.preventDefault();
            showAlert('O prazo deve ser posterior ao momento atual', 'warning');
            return false;
        }
    });
}

// Initialize timeline animations
function initializeTimelineAnimations() {
    // Animate timeline items on scroll
    $('.timeline-item').each(function() {
        const element = $(this);
        const elementTop = element.offset().top;
        const elementBottom = elementTop + element.outerHeight();
        const viewportTop = $(window).scrollTop();
        const viewportBottom = viewportTop + $(window).height();
        
        if (elementBottom > viewportTop && elementTop < viewportBottom) {
            element.addClass('animate__animated animate__fadeInLeft');
        }
    });
}

// Show custom alert
function showAlert(message, type = 'info') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    $('.content').prepend(alertHtml);
    
    // Auto-hide after 5 seconds
    setTimeout(function() {
        $('.alert').first().fadeOut('slow');
    }, 5000);
}

// Format date for display
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Format time remaining
function formatTimeRemaining(minutes) {
    if (minutes < 60) {
        return `${Math.round(minutes)} min`;
    } else if (minutes < 1440) {
        return `${Math.round(minutes / 60)}h`;
    } else {
        return `${Math.round(minutes / 1440)}d`;
    }
}

// Auto-save form data
function initializeAutoSave() {
    const forms = ['#sbar-form', '#ipass-form', '#pendency-form'];
    
    forms.forEach(formSelector => {
        const form = $(formSelector);
        if (form.length) {
            const formId = form.attr('id');
            
            // Load saved data
            const savedData = localStorage.getItem(`passometro_${formId}`);
            if (savedData) {
                const data = JSON.parse(savedData);
                Object.keys(data).forEach(key => {
                    const field = form.find(`[name="${key}"]`);
                    if (field.length) {
                        field.val(data[key]);
                    }
                });
            }
            
            // Save data on input change
            form.on('input change', function() {
                const formData = {};
                form.find('input, textarea, select').each(function() {
                    const field = $(this);
                    formData[field.attr('name')] = field.val();
                });
                
                localStorage.setItem(`passometro_${formId}`, JSON.stringify(formData));
            });
            
            // Clear saved data on successful submit
            form.on('submit', function() {
                localStorage.removeItem(`passometro_${formId}`);
            });
        }
    });
}

// Initialize search functionality
function initializeSearch() {
    $('#search-input').on('input', function() {
        const query = $(this).val().toLowerCase();
        
        $('.searchable-item').each(function() {
            const item = $(this);
            const text = item.text().toLowerCase();
            
            if (text.includes(query)) {
                item.show();
            } else {
                item.hide();
            }
        });
    });
}

// Initialize filters
function initializeFilters() {
    $('.filter-select').on('change', function() {
        const filterType = $(this).data('filter');
        const filterValue = $(this).val();
        
        $(`.filterable-item[data-${filterType}]`).each(function() {
            const item = $(this);
            const itemValue = item.data(filterType);
            
            if (filterValue === '' || itemValue === filterValue) {
                item.show();
            } else {
                item.hide();
            }
        });
    });
}

// Initialize sort functionality
function initializeSort() {
    $('.sortable').on('click', function() {
        const column = $(this).data('column');
        const direction = $(this).data('direction') === 'asc' ? 'desc' : 'asc';
        
        // Update all sortable headers
        $('.sortable').data('direction', 'asc').removeClass('sort-asc sort-desc');
        $(this).data('direction', direction).addClass(`sort-${direction}`);
        
        // Sort table
        const table = $(this).closest('table');
        const tbody = table.find('tbody');
        const rows = tbody.find('tr').toArray();
        
        rows.sort(function(a, b) {
            const aValue = $(a).find(`[data-${column}]`).data(column);
            const bValue = $(b).find(`[data-${column}]`).data(column);
            
            if (direction === 'asc') {
                return aValue > bValue ? 1 : -1;
            } else {
                return aValue < bValue ? 1 : -1;
            }
        });
        
        tbody.empty().append(rows);
    });
}

// Initialize print functionality
function initializePrint() {
    $('.print-btn').on('click', function() {
        window.print();
    });
}

// Initialize export functionality
function initializeExport() {
    $('.export-btn').on('click', function() {
        const format = $(this).data('format');
        const tableId = $(this).data('table');
        
        if (format === 'csv') {
            exportToCSV(tableId);
        } else if (format === 'pdf') {
            exportToPDF(tableId);
        }
    });
}

// Export table to CSV
function exportToCSV(tableId) {
    const table = $(`#${tableId}`);
    const headers = [];
    const rows = [];
    
    // Get headers
    table.find('thead th').each(function() {
        headers.push($(this).text().trim());
    });
    
    // Get rows
    table.find('tbody tr').each(function() {
        const row = [];
        $(this).find('td').each(function() {
            row.push($(this).text().trim());
        });
        rows.push(row);
    });
    
    // Create CSV content
    let csvContent = headers.join(',') + '\n';
    rows.forEach(row => {
        csvContent += row.join(',') + '\n';
    });
    
    // Download file
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${tableId}_export.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
}

// Initialize all functionality
$(document).ready(function() {
    initializeAutoSave();
    initializeSearch();
    initializeFilters();
    initializeSort();
    initializePrint();
    initializeExport();
}); 