// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S9.4-01)
// ============================================================================
// part_id           : S9.4-01
// parent_bom_id     : S9.4
// subsystem         : S9
// part_name         : Option-Q OVC -X CF63 Kriyo-Koaksiyel (4-Port 4-8 GHz) & 1550 nm SMF-28 Vakum Gecisi (Exp142 S9.1-01, 3.20 kg)
// material          : 316LN
// temp_stage        : 300 K (OVC portu)
// vacuum_grade      : Kriyo-vakum
// tolerance         : He<=1e-10 mbar*L/s
// computed_mass_kg  : 3.22425
// envelope_mm       : 100.000 x 120.000 x 120.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 100.0000;
bbox_y = 120.0000;
bbox_z = 120.0000;

// Part-specific parametric dimensions
cf_size = "CF63";
n_sma = 4;
fiber_nm = 1550.0;
mass_kg = 3.2;

// Interface / port parameters (mm)
port_ovc_west_cf63_od = 113.500;
port_ovc_west_cf63_bore = 50.000;
port_ovc_west_cf63_pcd = 92.100;
port_ovc_west_cf63_bolts = 8;
port_fiber_1550nm_smf28_bore = 9.600;

module part_S9_4_01() {
  union() {
    // ISO 3669 CF63 vacuum flange
    translate([41.250, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=113.500, h=17.500, center=true);
        cylinder(d=50.000, h=19.500, center=true);
        translate([0, 0, 7.500]) cylinder(d=82.400, h=1.750);
        for (i = [0 : 8 - 1])
          rotate([0, 0, i * 360 / 8])
            translate([46.050, 0, 0])
              cylinder(d=8.400, h=19.500, center=true);
      }
    }
    // 316LN vacuum spool
    translate([1.150, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=76.000, h=62.300, center=true);
        cylinder(d=50.000, h=64.300, center=true);
      }
    }
    // 4x SMA + 1550 nm SMF-28 bulkhead
    translate([-34.050, 0.000, 0.000]) cube([7.900, 120.000, 120.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-876.000, 0.000, 690.000]) rotate([0.000, 0.000, 0.000]) part_S9_4_01();

part_S9_4_01();
