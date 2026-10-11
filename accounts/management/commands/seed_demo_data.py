import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from accounts.models import CustomUser
from departments.models import Department
from employees.models import Employee
from attendance.models import Attendance
from leave_management.models import LeaveType, LeaveBalance, LeaveRequest
from payroll.models import SalaryStructure, PayrollRecord
from notifications.models import Notification
from audit.models import AuditLog

class Command(BaseCommand):
    help = "Seeds database with comprehensive fictional demo data across all modules."

    def handle(self, *args, **options):
        self.stdout.write("Starting demo data seeding...")

        with transaction.atomic():
            # 1. Create Core Users
            super_admin, _ = CustomUser.objects.get_or_create(
                username='superadmin',
                defaults={
                    'email': 'admin@enterprisehr.com',
                    'first_name': 'Alexander',
                    'last_name': 'Pierce',
                    'role': CustomUser.Role.SUPER_ADMIN,
                    'is_staff': True,
                    'is_superuser': True,
                    'phone_number': '+1 555-0101'
                }
            )
            super_admin.set_password('Admin@123')
            super_admin.save()

            hr_admin, _ = CustomUser.objects.get_or_create(
                username='hradmin',
                defaults={
                    'email': 'hr@enterprisehr.com',
                    'first_name': 'Sarah',
                    'last_name': 'Jenkins',
                    'role': CustomUser.Role.HR_ADMIN,
                    'is_staff': True,
                    'phone_number': '+1 555-0102'
                }
            )
            hr_admin.set_password('Admin@123')
            hr_admin.save()

            mgr_eng_user, _ = CustomUser.objects.get_or_create(
                username='mgr_eng',
                defaults={
                    'email': 'robert.chen@enterprisehr.com',
                    'first_name': 'Robert',
                    'last_name': 'Chen',
                    'role': CustomUser.Role.MANAGER,
                    'phone_number': '+1 555-0103'
                }
            )
            mgr_eng_user.set_password('Admin@123')
            mgr_eng_user.save()

            mgr_fin_user, _ = CustomUser.objects.get_or_create(
                username='mgr_fin',
                defaults={
                    'email': 'elena.rostova@enterprisehr.com',
                    'first_name': 'Elena',
                    'last_name': 'Rostova',
                    'role': CustomUser.Role.MANAGER,
                    'phone_number': '+1 555-0104'
                }
            )
            mgr_fin_user.set_password('Admin@123')
            mgr_fin_user.save()

            # 2. Create Departments
            dept_eng, _ = Department.objects.get_or_create(
                code='ENG',
                defaults={'name': 'Engineering & Technology', 'description': 'Software architecture, cloud systems, and product development.'}
            )
            dept_hr, _ = Department.objects.get_or_create(
                code='HR',
                defaults={'name': 'Human Resources', 'description': 'Talent acquisition, organizational development, and employee relations.'}
            )
            dept_fin, _ = Department.objects.get_or_create(
                code='FIN',
                defaults={'name': 'Finance & Operations', 'description': 'Financial planning, accounting, compliance, and corporate payroll.'}
            )

            # 3. Create Leave Types
            lt_cl, _ = LeaveType.objects.get_or_create(code='CL', defaults={'name': 'Casual Leave', 'default_days_per_year': 12, 'is_paid': True})
            lt_sl, _ = LeaveType.objects.get_or_create(code='SL', defaults={'name': 'Sick Leave', 'default_days_per_year': 10, 'is_paid': True, 'requires_attachment': True})
            lt_el, _ = LeaveType.objects.get_or_create(code='EL', defaults={'name': 'Earned / Annual Leave', 'default_days_per_year': 15, 'is_paid': True})
            lt_ul, _ = LeaveType.objects.get_or_create(code='UL', defaults={'name': 'Unpaid Leave', 'default_days_per_year': 30, 'is_paid': False})

            all_leave_types = [lt_cl, lt_sl, lt_el, lt_ul]

            # 4. Create Manager Employees
            emp_hr_admin, _ = Employee.objects.get_or_create(
                employee_id='EMP-2026-0001',
                defaults={
                    'user': hr_admin,
                    'first_name': 'Sarah',
                    'last_name': 'Jenkins',
                    'email': 'hr@enterprisehr.com',
                    'phone': '+1 555-0102',
                    'date_of_birth': datetime.date(1988, 4, 12),
                    'gender': Employee.Gender.FEMALE,
                    'department': dept_hr,
                    'designation': 'HR Lead & Operations Director',
                    'employment_status': Employee.Status.ACTIVE,
                    'basic_salary': Decimal('75000.00'),
                    'date_of_joining': datetime.date(2021, 3, 1),
                }
            )
            dept_hr.manager = emp_hr_admin
            dept_hr.save()

            emp_mgr_eng, _ = Employee.objects.get_or_create(
                employee_id='EMP-2026-0002',
                defaults={
                    'user': mgr_eng_user,
                    'first_name': 'Robert',
                    'last_name': 'Chen',
                    'email': 'robert.chen@enterprisehr.com',
                    'phone': '+1 555-0103',
                    'date_of_birth': datetime.date(1985, 9, 20),
                    'gender': Employee.Gender.MALE,
                    'department': dept_eng,
                    'designation': 'VP of Engineering',
                    'employment_status': Employee.Status.ACTIVE,
                    'basic_salary': Decimal('95000.00'),
                    'date_of_joining': datetime.date(2020, 1, 15),
                }
            )
            dept_eng.manager = emp_mgr_eng
            dept_eng.save()

            emp_mgr_fin, _ = Employee.objects.get_or_create(
                employee_id='EMP-2026-0003',
                defaults={
                    'user': mgr_fin_user,
                    'first_name': 'Elena',
                    'last_name': 'Rostova',
                    'email': 'elena.rostova@enterprisehr.com',
                    'phone': '+1 555-0104',
                    'date_of_birth': datetime.date(1987, 11, 5),
                    'gender': Employee.Gender.FEMALE,
                    'department': dept_fin,
                    'designation': 'Chief Financial Officer',
                    'employment_status': Employee.Status.ACTIVE,
                    'basic_salary': Decimal('90000.00'),
                    'date_of_joining': datetime.date(2020, 6, 1),
                }
            )
            dept_fin.manager = emp_mgr_fin
            dept_fin.save()

            # 5. Create 10 Additional Employees with user accounts
            employee_data = [
                ('David', 'Miller', 'david.miller@enterprisehr.com', '+1 555-0110', datetime.date(1992, 2, 14), Employee.Gender.MALE, dept_eng, 'Lead Backend Engineer', emp_mgr_eng, Decimal('65000.00'), datetime.date(2022, 2, 1)),
                ('Emily', 'Watson', 'emily.watson@enterprisehr.com', '+1 555-0111', datetime.date(1994, 7, 22), Employee.Gender.FEMALE, dept_eng, 'Senior Frontend Architect', emp_mgr_eng, Decimal('62000.00'), datetime.date(2022, 5, 15)),
                ('Michael', 'Chang', 'michael.chang@enterprisehr.com', '+1 555-0112', datetime.date(1995, 10, 30), Employee.Gender.MALE, dept_eng, 'DevOps & Cloud Engineer', emp_mgr_eng, Decimal('58000.00'), datetime.date(2023, 1, 10)),
                ('Priya', 'Sharma', 'priya.sharma@enterprisehr.com', '+1 555-0113', datetime.date(1996, 3, 18), Employee.Gender.FEMALE, dept_eng, 'Full-Stack Developer', emp_mgr_eng, Decimal('50000.00'), datetime.date(2023, 7, 1)),
                ('Lucas', 'Silva', 'lucas.silva@enterprisehr.com', '+1 555-0114', datetime.date(1998, 12, 1), Employee.Gender.MALE, dept_eng, 'Junior QA Automation Engineer', emp_mgr_eng, Decimal('40000.00'), datetime.date(2024, 1, 15)),
                ('Jessica', 'Taylor', 'jessica.taylor@enterprisehr.com', '+1 555-0115', datetime.date(1991, 5, 19), Employee.Gender.FEMALE, dept_hr, 'Senior Talent Acquisition Partner', emp_hr_admin, Decimal('52000.00'), datetime.date(2022, 8, 1)),
                ('Daniel', 'Kim', 'daniel.kim@enterprisehr.com', '+1 555-0116', datetime.date(1993, 8, 8), Employee.Gender.MALE, dept_hr, 'HR Operations Specialist', emp_hr_admin, Decimal('45000.00'), datetime.date(2023, 3, 1)),
                ('Marcus', 'Vance', 'marcus.vance@enterprisehr.com', '+1 555-0117', datetime.date(1989, 1, 25), Employee.Gender.MALE, dept_fin, 'Senior Financial Analyst', emp_mgr_fin, Decimal('60000.00'), datetime.date(2021, 11, 1)),
                ('Sophia', 'Martinez', 'sophia.martinez@enterprisehr.com', '+1 555-0118', datetime.date(1995, 6, 12), Employee.Gender.FEMALE, dept_fin, 'Corporate Accountant', emp_mgr_fin, Decimal('48000.00'), datetime.date(2023, 9, 15)),
                ('Aiden', 'Brown', 'aiden.brown@enterprisehr.com', '+1 555-0119', datetime.date(2000, 4, 3), Employee.Gender.MALE, dept_fin, 'Junior Billing Specialist', emp_mgr_fin, Decimal('36000.00'), datetime.date(2024, 2, 1)),
            ]

            created_employees = [emp_hr_admin, emp_mgr_eng, emp_mgr_fin]

            for idx, item in enumerate(employee_data, start=4):
                fn, ln, email, phone, dob, gender, dept, desig, rep, basic, doj = item
                username = email.split('@')[0].replace('.', '_')
                
                usr, _ = CustomUser.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'first_name': fn,
                        'last_name': ln,
                        'role': CustomUser.Role.EMPLOYEE,
                        'phone_number': phone
                    }
                )
                usr.set_password('Password@123')
                usr.save()

                emp, _ = Employee.objects.get_or_create(
                    employee_id=f"EMP-2026-{idx:04d}",
                    defaults={
                        'user': usr,
                        'first_name': fn,
                        'last_name': ln,
                        'email': email,
                        'phone': phone,
                        'date_of_birth': dob,
                        'gender': gender,
                        'department': dept,
                        'designation': desig,
                        'reporting_manager': rep,
                        'employment_status': Employee.Status.ACTIVE,
                        'basic_salary': basic,
                        'date_of_joining': doj,
                    }
                )
                created_employees.append(emp)

            # 6. Initialize Leave Balances and Salary Structures
            current_year = timezone.localdate().year
            today = timezone.localdate()

            for emp in created_employees:
                for lt in all_leave_types:
                    LeaveBalance.objects.get_or_create(
                        employee=emp,
                        leave_type=lt,
                        year=current_year,
                        defaults={
                            'total_allocated': Decimal(lt.default_days_per_year),
                            'used': Decimal('0.00'),
                            'remaining': Decimal(lt.default_days_per_year)
                        }
                    )

                SalaryStructure.objects.get_or_create(
                    employee=emp,
                    defaults={
                        'basic_salary': emp.basic_salary,
                        'hra': emp.basic_salary * Decimal('0.40'),
                        'transport_allowance': Decimal('2000.00'),
                        'medical_allowance': Decimal('1500.00'),
                        'special_allowance': Decimal('1000.00'),
                        'pf_rate_percent': Decimal('12.00'),
                        'professional_tax': Decimal('200.00'),
                    }
                )

            # 7. Create Attendance for Today and Recent Week
            for i in range(5):
                d = today - datetime.timedelta(days=i)
                if d.weekday() >= 5:  # Skip weekends
                    continue
                for emp in created_employees:
                    # Give diverse attendance statuses
                    if emp.employee_id == 'EMP-2026-0005' and i == 0:
                        status = Attendance.Status.ABSENT
                        cin, cout = None, None
                        late = False
                    elif emp.employee_id == 'EMP-2026-0006' and i == 0:
                        status = Attendance.Status.HALF_DAY
                        cin = datetime.time(9, 15, 0)
                        cout = datetime.time(13, 30, 0)
                        late = False
                    elif emp.employee_id == 'EMP-2026-0007':
                        status = Attendance.Status.PRESENT
                        cin = datetime.time(9, 45, 0)
                        cout = datetime.time(18, 45, 0)
                        late = True
                    else:
                        status = Attendance.Status.PRESENT
                        cin = datetime.time(9, 5, 0)
                        cout = datetime.time(18, 10, 0)
                        late = False

                    att, _ = Attendance.objects.get_or_create(
                        employee=emp,
                        attendance_date=d,
                        defaults={
                            'check_in': cin,
                            'check_out': cout,
                            'status': status,
                            'is_late': late,
                            'created_by': hr_admin
                        }
                    )

            # 8. Create Leave Requests in different statuses
            emp_david = created_employees[3]
            emp_emily = created_employees[4]
            emp_michael = created_employees[5]

            # Pending request
            lr_pending, _ = LeaveRequest.objects.get_or_create(
                request_id=f"LR-{current_year}-0001",
                defaults={
                    'employee': emp_david,
                    'leave_type': lt_cl,
                    'start_date': today + datetime.timedelta(days=3),
                    'end_date': today + datetime.timedelta(days=4),
                    'days_count': Decimal('2.0'),
                    'reason': 'Family function out of town.',
                    'status': LeaveRequest.Status.PENDING
                }
            )

            # Approved request
            lr_approved, _ = LeaveRequest.objects.get_or_create(
                request_id=f"LR-{current_year}-0002",
                defaults={
                    'employee': emp_emily,
                    'leave_type': lt_sl,
                    'start_date': today - datetime.timedelta(days=10),
                    'end_date': today - datetime.timedelta(days=9),
                    'days_count': Decimal('2.0'),
                    'reason': 'Acute fever and doctor advised rest.',
                    'status': LeaveRequest.Status.APPROVED,
                    'reviewed_by': hr_admin,
                    'review_comments': 'Approved. Medical slip attached.',
                    'reviewed_at': timezone.now() - datetime.timedelta(days=11)
                }
            )
            # Update Emily's sick leave balance
            bal_emily = LeaveBalance.objects.filter(employee=emp_emily, leave_type=lt_sl, year=current_year).first()
            if bal_emily:
                bal_emily.used = Decimal('2.0')
                bal_emily.save()

            # Rejected request
            lr_rejected, _ = LeaveRequest.objects.get_or_create(
                request_id=f"LR-{current_year}-0003",
                defaults={
                    'employee': emp_michael,
                    'leave_type': lt_el,
                    'start_date': today + datetime.timedelta(days=1),
                    'end_date': today + datetime.timedelta(days=7),
                    'days_count': Decimal('5.0'),
                    'reason': 'Vacation trip.',
                    'status': LeaveRequest.Status.REJECTED,
                    'reviewed_by': mgr_eng_user,
                    'review_comments': 'Project release milestone scheduled this week. Please reschedule.',
                    'reviewed_at': timezone.now() - datetime.timedelta(days=1)
                }
            )

            # 9. Create Historical Payroll for Previous Month
            prev_month = today.month - 1 if today.month > 1 else 12
            prev_year = today.year if today.month > 1 else today.year - 1

            for emp in created_employees[:8]:
                basic = emp.basic_salary
                hra = basic * Decimal('0.40')
                allowances = Decimal('4500.00')
                gross = basic + hra + allowances
                pf = (basic * Decimal('0.12')).quantize(Decimal('0.01'))
                ptax = Decimal('200.00')
                tot_ded = pf + ptax
                net = gross - tot_ded

                PayrollRecord.objects.get_or_create(
                    employee=emp,
                    month=prev_month,
                    year=prev_year,
                    defaults={
                        'payslip_number': f"PAY-{prev_year}{prev_month:02d}-{emp.pk:04d}",
                        'basic_salary': basic,
                        'hra': hra,
                        'allowances_total': allowances,
                        'bonus': Decimal('0.00'),
                        'gross_salary': gross,
                        'pf_deduction': pf,
                        'tax_deduction': ptax,
                        'unpaid_leave_deduction': Decimal('0.00'),
                        'total_deductions': tot_ded,
                        'net_salary': net,
                        'status': PayrollRecord.Status.PAID,
                        'payment_date': datetime.date(prev_year, prev_month, 28),
                        'processed_by': hr_admin
                    }
                )

            # 10. Notifications
            Notification.objects.get_or_create(
                user=mgr_eng_user,
                title="New Leave Request",
                defaults={
                    'message': "David Miller submitted a leave request (Casual Leave) from upcoming Friday.",
                    'notification_type': Notification.NotificationType.LEAVE,
                    'link': f"/leave/{lr_pending.pk}/"
                }
            )
            Notification.objects.get_or_create(
                user=emp_david.user,
                title="Payroll Credited",
                defaults={
                    'message': f"Your salary for {prev_month}/{prev_year} has been credited to your account.",
                    'notification_type': Notification.NotificationType.PAYROLL
                }
            )

            # 11. Initial Audit Logs
            AuditLog.objects.get_or_create(
                action='CREATE',
                object_type='System',
                object_id='INITIAL_SEED',
                defaults={
                    'actor': super_admin,
                    'change_summary': 'Executed seed_demo_data command to initialize departments, roles, and employee records.',
                    'ip_address': '127.0.0.1'
                }
            )

        self.stdout.write(self.style.SUCCESS("Demo data successfully created!"))
        self.stdout.write(self.style.SUCCESS("Test Accounts:"))
        self.stdout.write("  Super Admin : superadmin / Admin@123")
        self.stdout.write("  HR Admin    : hradmin / Admin@123")
        self.stdout.write("  Engineering Manager : mgr_eng / Admin@123")
        self.stdout.write("  Finance Manager     : mgr_fin / Admin@123")
        self.stdout.write("  Employee (e.g. David Miller) : david_miller / Password@123")
