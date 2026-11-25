// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.2-04)
// ============================================================================
// part_id           : S1.2-04
// parent_bom_id     : S1.2
// subsystem         : S1
// part_name         : Mikrometrik kutle-secim cikis yarigi (UHV lineer gecis)
// material          : 316LN
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-8 mbar
// tolerance         : ±2 um tekrarlanabilirlik
// computed_mass_kg  : 1.46578
// envelope_mm       : 84.000 x 325.000 x 33.800
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 84.0000;
bbox_y = 325.0000;
bbox_z = 33.8000;

// Part-specific parametric dimensions
collar_od = 84.0;
bellows_conv = 12;
slit_min_um = 20.0;
slit_max_um = 500.0;

// Interface / port parameters (mm)
port_slit_drive_pos_y_od = 33.800;
port_slit_drive_pos_y_bore = 14.000;
port_slit_drive_pos_y_pcd = 27.000;
port_slit_drive_pos_y_bolts = 6;
port_slit_drive_neg_y_od = 33.800;
port_slit_drive_neg_y_bore = 14.000;
port_slit_drive_neg_y_pcd = 27.000;
port_slit_drive_neg_y_bolts = 6;

module part_S1_2_04() {
  union() {
    // 316LN Wien exit slit collar
    difference() {
      cylinder(d=84.000, h=33.340, center=true);
      cylinder(d=44.000, h=35.340, center=true);
    }
    // +Y CF16 bellows drive flange
    translate([0.000, 74.000, 0.000]) rotate([-90.000, 0.000, 0.000]) {
      difference() {
        cylinder(d=33.800, h=7.500, center=true);
        cylinder(d=14.000, h=9.500, center=true);
        translate([0, 0, 2.650]) cylinder(d=21.300, h=1.600);
        for (i = [0 : 6 - 1])
          rotate([0, 0, i * 360 / 6])
            translate([13.500, 0, 0])
              cylinder(d=4.300, h=9.500, center=true);
      }
    }
    // -Y CF16 bellows drive flange
    translate([0.000, -74.000, 0.000]) rotate([90.000, 0.000, 0.000]) {
      difference() {
        cylinder(d=33.800, h=7.500, center=true);
        cylinder(d=14.000, h=9.500, center=true);
        translate([0, 0, 2.650]) cylinder(d=21.300, h=1.600);
        for (i = [0 : 6 - 1])
          rotate([0, 0, i * 360 / 6])
            translate([13.500, 0, 0])
              cylinder(d=4.300, h=9.500, center=true);
      }
    }
    // +Y Mo slit blade
    translate([0.000, 10.500, 0.000]) cube([28.000, 20.000, 8.500], center=true);
    // -Y Mo slit blade
    translate([0.000, -10.500, 0.000]) cube([28.000, 20.000, 8.500], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 234.330]) rotate([0.000, 0.000, 0.000]) part_S1_2_04();

part_S1_2_04();
