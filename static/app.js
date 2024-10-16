document.addEventListener('DOMContentLoaded', function() {
    const newEntryBtn = document.getElementById('newEntryBtn');
    const filterBtn = document.getElementById('filterBtn');
    const newEntryModal = document.getElementById('input-section');
    const filterModal = document.getElementById('filter-section');
    const closeBtns = document.getElementsByClassName('close');

    function openModal(modal) {
        modal.style.display = 'block';
    }

    function closeModal(modal) {
        modal.style.display = 'none';
    }

    newEntryBtn.onclick = function() {
        openModal(newEntryModal);
    }

    filterBtn.onclick = function() {
        openModal(filterModal);
    }

    Array.from(closeBtns).forEach(btn => {
        btn.onclick = function() {
            closeModal(this.closest('.modal'));
        }
    });

    window.onclick = function(event) {
        if (event.target.classList.contains('modal')) {
            closeModal(event.target);
        }
    }

    const expenseForm = document.getElementById('expenseForm');
    const entriesList = document.getElementById('entriesList');
    const loadMoreBtn = document.getElementById('loadMore');
    const applyFilterBtn = document.getElementById('applyFilter');
    const exportCSVBtn = document.getElementById('exportCSV');
    const toggleThemeBtn = document.getElementById('toggleTheme');

     function updateSummary() {
        fetch('/summary')
        .then(response => response.json())
        .then(data => {
            document.querySelector('#totalExpense .amount').textContent = `₹${data.totalExpense.toFixed(2)}`;
            document.querySelector('#totalIncome .amount').textContent = `₹${data.totalIncome.toFixed(2)}`;
            document.querySelector('#netBalance .amount').textContent = `₹${data.netBalance.toFixed(2)}`;
        })
        .catch(error => console.error('Error:', error));

    }

    updateSummary();

    expenseForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const data = Object.fromEntries(formData.entries());

        fetch('/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            console.log('Success:', data);
            alert('Entry added successfully!');
            expenseForm.reset();
            loadEntries();
            updateSummary();  // Add this line to update the summary after adding a new entry
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('Error adding entry. Please try again.');
        });
    });

    function loadEntries(page = 1) {
        fetch(`/expenses?page=${page}`)
        .then(response => response.json())
        .then(data => {
            if (page === 1) {
                entriesList.innerHTML = '';
            }
            data.forEach(entry => {
                const entryElement = document.createElement('div');
                entryElement.className = 'entry-item';
                entryElement.innerHTML = `
                    <span>${entry.date}: ${entry.description}</span>
                    <span>${entry.type === 'expense' ? '-' : '+'}₹${entry.amount}</span>
                `;
                entriesList.appendChild(entryElement);
            });
        })
        .catch(error => console.error('Error:', error));
    }

    loadMoreBtn.addEventListener('click', function() {
        const currentPage = Math.ceil(entriesList.children.length / 10) + 1;
        loadEntries(currentPage);
    });

    applyFilterBtn.addEventListener('click', function() {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const category = document.getElementById('filterCategory').value;
        
        fetch(`/expenses?startDate=${startDate}&endDate=${endDate}&category=${category}`)
        .then(response => response.json())
        .then(data => {
            entriesList.innerHTML = '';
            data.forEach(entry => {
                const entryElement = document.createElement('div');
                entryElement.className = 'entry-item';
                entryElement.innerHTML = `
                    <span>${entry.date}: ${entry.description}</span>
                    <span>${entry.type === 'expense' ? '-' : '+'}₹${entry.amount}</span>
                `;
                entriesList.appendChild(entryElement);
            });
        })
        .catch(error => console.error('Error:', error));
    });

    exportCSVBtn.addEventListener('click', function() {
        window.location.href = '/export';
    });

    toggleThemeBtn.addEventListener('click', function() {
        document.body.classList.toggle('dark-mode');
    });

    // Initial load of entries
    loadEntries();
});