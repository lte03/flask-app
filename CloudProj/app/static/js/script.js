document.addEventListener("DOMContentLoaded", function() {
	const alerts = document.querySelectorAll('.alert');
	alerts.forEach(alert => {
		setTimeout(() => {
			alert.style.opacity = '0';
			setTimeout(() => {
				alert.remove();
			}, 500);
		}, 5000);
	});
});