// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.5-02)
// ============================================================================
// part_id           : S6.5-02
// parent_bom_id     : S6.5
// subsystem         : S6
// part_name         : Genis-bantli RF guc yukselticileri ve yonlu kuplorler
// material          : Al 6061
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Atmosfer
// tolerance         : ±0.5 dB
// computed_mass_kg  : 9.57064
// envelope_mm       : 482.600 x 492.050 x 86.900
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 492.0500;
bbox_z = 86.9000;

// Part-specific parametric dimensions
rack_u = 2;
p_out_w = 10.0;
f_max_mhz = 200.0;

// Interface / port parameters (mm)

module part_S6_5_02() {
  difference() {
    union() {
      // 19" EIA-310 front bezel panel
      translate([0.000, -238.000, 0.000]) cube([482.600, 4.000, 86.900], center=true);
      // Hollow EMI shielded chassis body
      translate([0.000, 2.050, 0.000]) cube([440.000, 475.900, 85.900], center=true);
    }
    // EIA-310 rack ear slot
    translate([-232.600, -238.000, -27.808]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([-232.600, -238.000, 27.808]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -238.000, -27.808]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -238.000, 27.808]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([2100.000, 0.000, 578.950]) rotate([0.000, 0.000, 0.000]) part_S6_5_02();

part_S6_5_02();
