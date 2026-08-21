/**
 * initialize footer and lookup loading behavior
 * :returns: none
 */
document.addEventListener("DOMContentLoaded", () => {
    const yearSpan = document.getElementById('current-year');
    if (yearSpan) {
        yearSpan.textContent = new Date().getFullYear();
    }

    const lookupForm = document.getElementById('lookup-form');
    if (lookupForm) {
        const searchContainer = document.querySelector('.search-container');
        const loadingPanel = document.getElementById('loading-panel');
        const loadingStatus = document.getElementById('loading-status');
        const lookupButton = document.getElementById('lookup-button');
        const messages = [
            'Loading your Steam library...',
            'Checking game prices and achievements...',
            'Calculating supported inventory values...',
            'Preparing your results...'
        ];

        /**
         * show lookup progress after form submission
         * :returns: none
         */
        lookupForm.addEventListener('submit', () => {
            lookupButton.disabled = true;
            searchContainer.hidden = true;
            loadingPanel.hidden = false;

            let messageIndex = 0;
            /**
             * advance the displayed lookup progress message
             * :returns: none
             */
            window.setInterval(() => {
                loadingStatus.textContent = messages[messageIndex % messages.length];
                messageIndex += 1;
            }, 3500);
        });
    }
});


/**
 * sort game table rows using the selected order
 * :param order: selected table sort order
 * :returns: none
 */
function sortTable(order) {
    const table = document.querySelector('.games-list table tbody');
    if (!table) return;
    const rows = Array.from(table.querySelectorAll('tr'));
    const sortingMessage = document.getElementById('sorting-message');

    /**
     * compare two game table rows using the selected order
     * :param a: first game table row
     * :param b: second game table row
     * :returns: row sort position
     */
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

    /**
     * append a sorted game table row
     * :param row: game table row to append
     * :returns: appended game table row
     */
    rows.forEach(row => table.appendChild(row));
}
