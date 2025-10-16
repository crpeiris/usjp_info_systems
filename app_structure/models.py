from django.db import models
import uuid
from django.utils import timezone


# Accounts (simple extension for MVP)
class User(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	username = models.CharField(max_length=150, unique=True)
	email = models.EmailField(blank=True)
	is_active = models.BooleanField(default=True)

	class Meta:
		abstract = False

	def __str__(self):
		return self.username


class Manager(User):
	# Manager-specific fields can be added later
	class Meta:
		verbose_name = "Manager"


class Assistant(User):
	# Assistant-specific fields can be added later
	class Meta:
		verbose_name = "Assistant"


# Structure
class Zone(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	zone_id = models.CharField(max_length=50)
	zone_name = models.CharField(max_length=200)
	description = models.TextField(blank=True)

	def __str__(self):
		return self.zone_name


class Section(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	section_id = models.CharField(max_length=50)
	section_name = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="sections")

	def __str__(self):
		return self.section_name


class Faculty(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	faculty_id = models.CharField(max_length=50)
	faculty_name = models.CharField(max_length=200)

	def __str__(self):
		return self.faculty_name


class Unit(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	unit_id = models.CharField(max_length=50)
	unit_name = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	is_active = models.BooleanField(default=True)
	section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="units")
	faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="units", null=True, blank=True)

	def __str__(self):
		return self.unit_name


class AssistantAssignment(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	assistant = models.ForeignKey(Assistant, on_delete=models.CASCADE, related_name="assignments")
	unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="assistant_assignments")
	start_date = models.DateField()
	end_date = models.DateField(null=True, blank=True)

	class Meta:
		ordering = ["-start_date"]

	def __str__(self):
		return f"{self.assistant} @ {self.unit} ({self.start_date}..{self.end_date or 'present'})"


# Templates
class CSTemplate(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	name = models.CharField(max_length=200)
	version = models.PositiveIntegerField(default=1)
	is_draft = models.BooleanField(default=True)
	created_by = models.ForeignKey(Manager, on_delete=models.SET_NULL, null=True, related_name="created_templates")
	created_at = models.DateTimeField(default=timezone.now)
	month_days = models.PositiveSmallIntegerField(default=30)

	def __str__(self):
		return f"{self.name} v{self.version}"


class TemplateActivity(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	template = models.ForeignKey(CSTemplate, on_delete=models.CASCADE, related_name="activities")
	name = models.CharField(max_length=200)
	display_order = models.PositiveIntegerField(default=0)

	class Meta:
		ordering = ["display_order"]

	def __str__(self):
		return self.name


class UnitTemplateAssignment(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="template_assignments")
	template = models.ForeignKey(CSTemplate, on_delete=models.CASCADE, related_name="unit_assignments")
	start_date = models.DateField()
	end_date = models.DateField(null=True, blank=True)

	class Meta:
		ordering = ["-start_date"]

	def __str__(self):
		return f"{self.unit} -> {self.template} ({self.start_date})"


# Cleaning / Schedules
class Schedule(models.Model):
	class ScheduleStatus(models.TextChoices):
		DRAFT = "DRAFT", "Draft"
		ACTIVE = "ACTIVE", "Active"
		SUBMITTED = "SUBMITTED", "Submitted"
		CLOSED = "CLOSED", "Closed"
		ARCHIVED = "ARCHIVED", "Archived"

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="schedules")
	instantiated_from = models.ForeignKey(CSTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="schedules")
	month = models.DateField(help_text="first day of month")
	status = models.CharField(max_length=20, choices=ScheduleStatus.choices, default=ScheduleStatus.DRAFT)
	created_at = models.DateTimeField(default=timezone.now)
	submitted_at = models.DateTimeField(null=True, blank=True)
	closed_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		unique_together = ("unit", "month")

	def __str__(self):
		return f"Schedule {self.unit} - {self.month:%Y-%m} ({self.status})"


class ScheduleCell(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name="cells")
	day = models.PositiveSmallIntegerField()
	activity_name = models.CharField(max_length=200)
	budgeted = models.DecimalField(max_digits=7, decimal_places=2, default=0)
	actual = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
	notes = models.TextField(null=True, blank=True)

	class Meta:
		unique_together = ("schedule", "day")
		ordering = ["day"]

	def __str__(self):
		return f"{self.schedule} - day {self.day}: {self.activity_name}"


# Reporting / Archive
class ArchivedDocument(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	file_path = models.CharField(max_length=1000)
	generated_at = models.DateTimeField(default=timezone.now)
	mime_type = models.CharField(max_length=100)
	checksum = models.CharField(max_length=128, blank=True)
	tags_json = models.TextField(blank=True, help_text="zone,section,unit,faculty,year,month,assistant")
	schedule = models.OneToOneField(Schedule, on_delete=models.SET_NULL, null=True, blank=True, related_name="archived_document")

	def __str__(self):
		return f"ArchivedDocument {self.file_path} ({self.generated_at:%Y-%m-%d})"

