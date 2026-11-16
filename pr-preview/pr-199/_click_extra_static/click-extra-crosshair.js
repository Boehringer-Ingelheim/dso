(function (selector) {
  function ready(fn) {
    if (document.readyState !== "loading") {
      fn();
    } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }

  ready(function () {
    Array.prototype.forEach.call(document.querySelectorAll(selector), function (table) {
      // Mark each cell whose whole content is one link. A cell mixing a link
      // with other text, like a header with a footnote marker, is left alone.
      Array.prototype.forEach.call(table.querySelectorAll("td, th"), function (cell) {
        var links = cell.querySelectorAll("a[href]");
        if (
          links.length === 1 &&
          cell.textContent.trim() === links[0].textContent.trim()
        ) {
          cell.classList.add("linked-cell");
        }
      });

      // A merged cell shifts the cells after it in its row, so a cell index no
      // longer names a visual column.
      if (table.querySelector("[colspan], [rowspan]")) {
        return;
      }

      function clear() {
        var marked = table.querySelectorAll(
          ".crosshair-col, .crosshair-row, .crosshair-cell"
        );
        Array.prototype.forEach.call(marked, function (element) {
          element.classList.remove("crosshair-col", "crosshair-row", "crosshair-cell");
        });
      }

      table.addEventListener("mouseover", function (event) {
        var cell = event.target.closest("td, th");
        if (!cell || !table.contains(cell)) {
          return;
        }
        var column = cell.cellIndex;
        clear();
        // The column: the cell at the same index in every row, header included.
        Array.prototype.forEach.call(table.rows, function (row) {
          var columnCell = row.cells[column];
          if (columnCell) {
            columnCell.classList.add("crosshair-col");
          }
        });
        cell.parentElement.classList.add("crosshair-row");
        cell.classList.add("crosshair-cell");
      });

      table.addEventListener("mouseleave", clear);
    });
  });
})("table.corner-table");
