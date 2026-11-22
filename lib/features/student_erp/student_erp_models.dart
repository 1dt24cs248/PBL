class StudentProfile {
  const StudentProfile({
    required this.usn,
    required this.fullName,
    required this.branch,
    required this.department,
    required this.semester,
    required this.division,
    required this.sectionLabel,
    required this.sectionMappingStatus,
    required this.labBatch,
    required this.rollNo,
    required this.homeRoom,
    required this.dataStatus,
  });

  factory StudentProfile.fromJson(Map<String, dynamic> json) {
    final room = json['home_room'] as Map<String, dynamic>;
    return StudentProfile(
      usn: json['usn'] as String,
      fullName: json['full_name'] as String,
      branch: json['branch'] as String,
      department: json['department'] as String,
      semester: json['semester'] as int,
      division: json['division'] as String,
      sectionLabel: json['section_label'] as String,
      sectionMappingStatus: json['section_mapping_status'] as String,
      labBatch: json['lab_batch'] as String,
      rollNo: json['roll_no'] as int?,
      homeRoom: StudentHomeRoom.fromJson(room),
      dataStatus: json['data_status'] as String,
    );
  }

  final String usn;
  final String fullName;
  final String branch;
  final String department;
  final int semester;
  final String division;
  final String sectionLabel;
  final String sectionMappingStatus;
  final String labBatch;
  final int? rollNo;
  final StudentHomeRoom homeRoom;
  final String dataStatus;
}

class StudentHomeRoom {
  const StudentHomeRoom({required this.code, required this.realLabel});

  factory StudentHomeRoom.fromJson(Map<String, dynamic> json) =>
      StudentHomeRoom(
        code: json['code'] as String,
        realLabel: json['real_label'] as String,
      );

  final String code;
  final String realLabel;
}

class AttendanceData {
  const AttendanceData({required this.dataStatus, required this.days});

  factory AttendanceData.fromJson(Map<String, dynamic> json) => AttendanceData(
    dataStatus: json['data_status'] as String,
    days: (json['days'] as List<dynamic>)
        .map((item) => AttendanceDay.fromJson(item as Map<String, dynamic>))
        .toList(),
  );

  final String dataStatus;
  final List<AttendanceDay> days;
}

class AttendanceDay {
  const AttendanceDay({
    required this.date,
    required this.weekday,
    required this.slots,
  });

  factory AttendanceDay.fromJson(Map<String, dynamic> json) => AttendanceDay(
    date: json['date'] as String,
    weekday: json['weekday'] as String,
    slots: (json['slots'] as List<dynamic>)
        .map((item) => AttendanceSlot.fromJson(item as Map<String, dynamic>))
        .toList(),
  );

  final String date;
  final String weekday;
  final List<AttendanceSlot> slots;
}

class AttendanceSlot {
  const AttendanceSlot({
    required this.slot,
    required this.subjectCode,
    required this.subjectName,
    required this.status,
  });

  factory AttendanceSlot.fromJson(Map<String, dynamic> json) => AttendanceSlot(
    slot: json['slot'] as String?,
    subjectCode: json['subject_code'] as String?,
    subjectName: json['subject_name'] as String?,
    status: json['status'] as String,
  );

  final String? slot;
  final String? subjectCode;
  final String? subjectName;
  final String status;
}

class AttendanceSummary {
  const AttendanceSummary({
    required this.dataStatus,
    required this.overall,
    required this.subjects,
  });

  factory AttendanceSummary.fromJson(Map<String, dynamic> json) =>
      AttendanceSummary(
        dataStatus: json['data_status'] as String,
        overall: AttendanceOverall.fromJson(
          json['overall'] as Map<String, dynamic>,
        ),
        subjects: (json['subjects'] as List<dynamic>)
            .map(
              (item) =>
                  AttendanceSubject.fromJson(item as Map<String, dynamic>),
            )
            .toList(),
      );

  final String dataStatus;
  final AttendanceOverall overall;
  final List<AttendanceSubject> subjects;
}

class AttendanceOverall {
  const AttendanceOverall({
    required this.present,
    required this.absent,
    required this.noAttendance,
    required this.total,
    required this.percent,
  });

  factory AttendanceOverall.fromJson(Map<String, dynamic> json) =>
      AttendanceOverall(
        present: json['present'] as int,
        absent: json['absent'] as int,
        noAttendance: json['no_attendance'] as int,
        total: json['total'] as int,
        percent: (json['percent'] as num).toDouble(),
      );

  final int present;
  final int absent;
  final int noAttendance;
  final int total;
  final double percent;
}

class AttendanceSubject {
  const AttendanceSubject({
    required this.subjectCode,
    required this.subjectName,
    required this.component,
    required this.total,
    required this.present,
    required this.percent,
    required this.status,
  });

  factory AttendanceSubject.fromJson(Map<String, dynamic> json) =>
      AttendanceSubject(
        subjectCode: json['subject_code'] as String,
        subjectName: json['subject_name'] as String,
        component: json['component'] as String,
        total: json['total'] as int,
        present: json['present'] as int,
        percent: (json['percent'] as num).toDouble(),
        status: json['status'] as String,
      );

  final String subjectCode;
  final String subjectName;
  final String component;
  final int total;
  final int present;
  final double percent;
  final String status;
}

class LmsSubjects {
  const LmsSubjects({required this.dataStatus, required this.subjects});

  factory LmsSubjects.fromJson(Map<String, dynamic> json) => LmsSubjects(
    dataStatus: json['data_status'] as String,
    subjects: (json['subjects'] as List<dynamic>)
        .map((item) => LmsSubject.fromJson(item as Map<String, dynamic>))
        .toList(),
  );

  final String dataStatus;
  final List<LmsSubject> subjects;
}

class LmsSubject {
  const LmsSubject({
    required this.subjectCode,
    required this.altCode,
    required this.subjectName,
    required this.component,
    required this.semester,
    required this.facultyNames,
  });

  factory LmsSubject.fromJson(Map<String, dynamic> json) => LmsSubject(
    subjectCode: json['subject_code'] as String,
    altCode: json['alt_code'] as String?,
    subjectName: json['subject_name'] as String,
    component: json['component'] as String,
    semester: json['semester'] as int,
    facultyNames: (json['faculty_names'] as List<dynamic>)
        .map((item) => item.toString())
        .toList(),
  );

  final String subjectCode;
  final String? altCode;
  final String subjectName;
  final String component;
  final int semester;
  final List<String> facultyNames;
}

class AcademicHoliday {
  const AcademicHoliday({
    required this.date,
    required this.name,
    required this.source,
  });

  factory AcademicHoliday.fromJson(Map<String, dynamic> json) =>
      AcademicHoliday(
        date: json['date'] as String,
        name: json['name'] as String,
        source: json['source'] as String,
      );

  final String date;
  final String name;
  final String source;
}

class StudentFees {
  const StudentFees({
    required this.dataStatus,
    required this.ledger,
    required this.years,
    required this.scholarship,
  });

  factory StudentFees.fromJson(Map<String, dynamic> json) => StudentFees(
    dataStatus: json['data_status'] as String,
    ledger: FeesLedger.fromJson(json['ledger'] as Map<String, dynamic>),
    years: (json['years'] as List<dynamic>)
        .map((item) => FeesYear.fromJson(item as Map<String, dynamic>))
        .toList(),
    scholarship: FeesScholarship.fromJson(
      json['scholarship'] as Map<String, dynamic>,
    ),
  );

  final String dataStatus;
  final FeesLedger ledger;
  final List<FeesYear> years;
  final FeesScholarship scholarship;
}

class FeesLedger {
  const FeesLedger({
    required this.toBeCollected,
    required this.paid,
    required this.previous,
    required this.pending,
  });

  factory FeesLedger.fromJson(Map<String, dynamic> json) => FeesLedger(
    toBeCollected: json['to_be_collected'] as int,
    paid: json['paid'] as int,
    previous: json['previous'] as int,
    pending: json['pending'] as int,
  );

  final int toBeCollected;
  final int paid;
  final int previous;
  final int pending;
}

class FeesYear {
  const FeesYear({
    required this.year,
    required this.total,
    required this.receipts,
  });

  factory FeesYear.fromJson(Map<String, dynamic> json) => FeesYear(
    year: json['year'] as int,
    total: json['total'] as int,
    receipts: (json['receipts'] as List<dynamic>)
        .map((item) => FeeReceipt.fromJson(item as Map<String, dynamic>))
        .toList(),
  );

  final int year;
  final int total;
  final List<FeeReceipt> receipts;
}

class FeeReceipt {
  const FeeReceipt({
    required this.receiptNo,
    required this.date,
    required this.heads,
    required this.mode,
  });

  factory FeeReceipt.fromJson(Map<String, dynamic> json) => FeeReceipt(
    receiptNo: json['receipt_no'] as String,
    date: json['date'] as String,
    heads: (json['heads'] as List<dynamic>)
        .map((item) => FeeHead.fromJson(item as Map<String, dynamic>))
        .toList(),
    mode: json['mode'] as String,
  );

  final String receiptNo;
  final String date;
  final List<FeeHead> heads;
  final String mode;
}

class FeeHead {
  const FeeHead({required this.name, required this.amount});

  factory FeeHead.fromJson(Map<String, dynamic> json) =>
      FeeHead(name: json['name'] as String, amount: json['amount'] as int);

  final String name;
  final int amount;
}

class FeesScholarship {
  const FeesScholarship({required this.status, required this.note});

  factory FeesScholarship.fromJson(Map<String, dynamic> json) =>
      FeesScholarship(
        status: json['status'] as String,
        note: json['note'] as String,
      );

  final String status;
  final String note;
}
