// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S7.SAFETY-04)
// ============================================================================
// part_id           : S7.SAFETY-04
// parent_bom_id     : S7.SAFETY
// subsystem         : S7
// part_name         : 15 kVA / 10 kWh Online Cift-Donusumlu LFP UPS (0 ms Gecis) & Kademeli Yuk-Atma PDU (Exp150, 145.0 kg)
// material          : LFP
// temp_stage        : 300 K (tesis guc bolmesi)
// vacuum_grade      : Atmosfer
// tolerance         : 0 ms gecis, >=30 dk tam
// computed_mass_kg  : 145.00000
// envelope_mm       : 440.000 x 736.200 x 780.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 440.0000;
bbox_y = 736.2000;
bbox_z = 780.0000;

// Part-specific parametric dimensions
ups_w_mm = 440.0;
ups_d_mm = 720.0;
ups_h_mm = 780.0;
kva_rating = 15.0;
lfp_kwh = 10.0;

// Interface / port parameters (mm)

module part_S7_SAFETY_04() {
  difference() {
    union() {
      // 15 kVA / 10 kWh Online LFP UPS floor tower
      cube([440.000, 720.000, 780.000], center=true);
      // Tier-1 / Tier-2 load-shed breaker panel
      translate([0.000, 368.000, 120.000]) cube([340.000, 16.000, 260.000], center=true);
    }
    // Front LCD telemetry bezel
    translate([0.000, -355.000, 250.000]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-45.000, 0, 0]) cylinder(d=70.000, h=20.000, center=true);
        translate([45.000, 0, 0]) cylinder(d=70.000, h=20.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([2650.000, 150.000, 390.000]) rotate([0.000, 0.000, 0.000]) part_S7_SAFETY_04();

part_S7_SAFETY_04();
