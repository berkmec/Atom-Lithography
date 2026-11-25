// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.7-01)
// ============================================================================
// part_id           : S6.7-01
// parent_bom_id     : S6.7
// subsystem         : S6
// part_name         : SET / rf-SET kriyojenik tank-devresi on-uclari ve bias-tee modulleri
// material          : OFHC Cu
// temp_stage        : 20 mK (MXC)
// vacuum_grade      : UHV / Kriyo-vakum
// tolerance         : ±5% f_0
// computed_mass_kg  : 1.23359
// envelope_mm       : 188.000 x 188.000 x 33.250
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 188.0000;
bbox_y = 188.0000;
bbox_z = 33.2500;

// Part-specific parametric dimensions
n_rfset_modules = 56;
plate_od = 188.0;
f_tank_mhz = 320.0;

// Interface / port parameters (mm)
port_rfset_20mk_mount_od = 188.000;
port_rfset_20mk_mount_pcd = 172.000;
port_rfset_20mk_mount_bolts = 12;

module part_S6_7_01() {
  difference() {
    union() {
      // 20 mK rf-SET OFHC carrier
      translate([0.000, 0.000, 15.000]) {
        difference() {
          cylinder(d=188.000, h=5.500, center=true);
          cylinder(d=24.000, h=7.500, center=true);
        }
      }
      // 56x shielded rf-SET LC tank modules
      translate([0.000, 0.000, -2.500]) {
        difference() {
          cylinder(d=162.000, h=26.000, center=true);
          cylinder(d=74.000, h=28.000, center=true);
        }
      }
    }
    // 12x M3 clamp bolts
    translate([0.000, 0.000, 15.000]) {
      for (i = [0 : 12 - 1])
        rotate([0, 0, i * 360 / 12])
          translate([86.000, 0, 0])
            cylinder(d=3.200, h=8.000, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-650.000, 0.000, 310.000]) rotate([0.000, 0.000, 0.000]) part_S6_7_01();

part_S6_7_01();
