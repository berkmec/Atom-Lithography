// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.1-04)
// ============================================================================
// part_id           : S1.1-04
// parent_bom_id     : S1.1
// subsystem         : S1
// part_name         : UHV VCR kutle akis denetleyici ve kaynak gaz manifoldu
// material          : 316L
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±1% FS akis
// computed_mass_kg  : 1.67892
// envelope_mm       : 92.000 x 105.250 x 67.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 92.0000;
bbox_y = 105.2500;
bbox_z = 67.0000;

// Part-specific parametric dimensions
manifold_w = 92.0;
manifold_d = 40.0;
vcr_od = 12.7;

// Interface / port parameters (mm)
port_vcr_out_to_source_od = 12.700;
port_vcr_out_to_source_bore = 9.000;
port_vcr_in_from_cabinet_od = 9.500;
port_vcr_in_from_cabinet_bore = 6.400;

module part_S1_1_04() {
  union() {
    // 316L VAR VCR manifold block
    translate([0.000, -14.000, 0.000]) cube([92.000, 40.000, 44.000], center=true);
    // PH3 0.1-10 sccm MFC
    translate([-24.000, -14.000, 32.500]) cube([36.000, 32.000, 20.000], center=true);
    // SiF4 0.1-10 sccm MFC
    translate([24.000, -14.000, 32.500]) cube([36.000, 32.000, 20.000], center=true);
    // Coaxial VCR feed tube to S1.1-01
    translate([0.000, 35.000, 0.000]) rotate([90.000, 0.000, 0.000]) {
      difference() {
        cylinder(d=12.700, h=38.000, center=true);
        cylinder(d=9.000, h=40.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, -102.000, 492.660]) rotate([0.000, 0.000, 0.000]) part_S1_1_04();

part_S1_1_04();
