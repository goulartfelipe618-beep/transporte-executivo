/** Nexus Transfer - Motor de Reservas */
(function () {
  const dateInput = document.getElementById('trip_date');
  if (dateInput && !dateInput.value) {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    dateInput.min = tomorrow.toISOString().split('T')[0];
    dateInput.value = dateInput.min;
  }
})();
