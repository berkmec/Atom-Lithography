// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S7.SAFETY-03)
// ============================================================================
// part_id           : S7.SAFETY-03
// parent_bom_id     : S7.SAFETY
// subsystem         : S7
// part_name         : IEC 61508 SIL-3 1oo2D Donanimsal Emniyet PLC, 4x E-Stop Mantar, Kapak Anahtarlari & 2 MOhm HV Crowbar Modulu (Exp150, 18.0 kg)
// material          : Steel
// temp_stage        : 300 K (S7 raf ustu)
// vacuum_grade      : Atmosfer
// tolerance         : SIL-3 1oo2D, <50 ms HV
// computed_mass_kg  : 18.00000
// envelope_mm       : 4000.000 x 4000.000 x 1911.450
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 4000.0000;
bbox_y = 4000.0000;
bbox_z = 1911.4500;

// Part-specific parametric dimensions
plc_u = 3;
estop_corner_mm = 1900.0;
crowbar_mohm = 2.0;

// Interface / port parameters (mm)

module part_S7_SAFETY_03() {
  union() {
    // 3U 1oo2D safety PLC chassis (Bay 1 U39-U41)
    cube([482.600, 350.000, 133.400], center=true);
    // Active 2 MOhm HV crowbar dump box
    translate([-460.000, 500.000, -1100.000]) cube([220.000, 180.000, 160.000], center=true);
    // Representative corner E-Stop pedestal
    translate([-3300.000, -1650.000, -1320.000]) cylinder(d=60.000, h=1050.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([1480.000, -263.000, 1845.775]) rotate([0.000, 0.000, 0.000]) part_S7_SAFETY_03();

part_S7_SAFETY_03();
