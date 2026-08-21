// automatically update the year in the footer
document.addEventListener("DOMContentLoaded", () => {
    const yearSpan = document.getElementById('current-year');
    if (yearSpan) {
        yearSpan.textContent = new Date().getFullYear();
    }
});


// sorting table
function sortTable(order) {
    const table = document.querySelector('.games-list table tbody');
    const rows = Array.from(table.querySelectorAll('tr'));
    const sortingMessage = document.getElementById('sorting-message');

    rows.sort((a, b) => {
        const nameA = a.cells[1].textContent.trim().toLowerCase();
        const nameB = b.cells[1].textContent.trim().toLowerCase();
        const hoursA = parseFloat(a.cells[2].textContent.trim());
        const hoursB = parseFloat(b.cells[2].textContent.trim());
        const valueA = parseFloat(a.cells[4].dataset.value);
        const valueB = parseFloat(b.cells[4].dataset.value);

        if(order === 'hours-desc') {
            sortingMessage.textContent = 'Here are your Steam games sorted by playtime (highest to lowest)';
            return hoursB - hoursA;
        } else if(order === 'hours-asc') {
            sortingMessage.textContent = 'Here are your Steam games sorted by playtime (lowest to highest)';
            return hoursA - hoursB;
        } else if(order === 'alpha-desc') {
            sortingMessage.textContent = 'Here are your Steam games sorted alphabetically (Z to A)';
            return nameB.localeCompare(nameA);
        } else if(order === 'alpha-asc') {
            sortingMessage.textContent = 'Here are your Steam games sorted alphabetically (A to Z)';
            return nameA.localeCompare(nameB);
        } else if(order === 'value-desc') {
            sortingMessage.textContent = 'Here are your Steam games sorted by value (highest to lowest)';
            if (Number.isNaN(valueA) && Number.isNaN(valueB)) return 0;
            if (Number.isNaN(valueA)) return 1;
            if (Number.isNaN(valueB)) return -1;
            return valueB - valueA;
        } else if(order === 'value-asc') {
            sortingMessage.textContent = 'Here are your Steam games sorted by value (lowest to highest)';
            if (Number.isNaN(valueA) && Number.isNaN(valueB)) return 0;
            if (Number.isNaN(valueA)) return 1;
            if (Number.isNaN(valueB)) return -1;
            return valueA - valueB;
        }
    });

    // re-append sorted rows
    rows.forEach(row => table.appendChild(row));
}
