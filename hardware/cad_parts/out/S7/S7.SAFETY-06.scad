// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S7.SAFETY-06)
// ============================================================================
// part_id           : S7.SAFETY-06
// parent_bom_id     : S7.SAFETY
// subsystem         : S7
// part_name         : Hizli Yay-Donuslu UHV Izolasyon Surgu Vana Aktorleri (<80 ms), ISO 10156 %5 H2/N2 Orifis & X-Isini Dozimetresi (Exp150, 12.0 kg)
// material          : 316LN
// temp_stage        : 300 K (S5 manifold / oda)
// vacuum_grade      : UHV / Atmosfer
// tolerance         : <80 ms vana, <=0.01 ML
// computed_mass_kg  : 12.00000
// envelope_mm       : 218.950 x 146.000 x 163.750
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 218.9500;
bbox_y = 146.0000;
bbox_z = 163.7500;

// Part-specific parametric dimensions
close_time_ms = 80.0;
bonnet_cf = "CF63";
orifice_bore_mm = 0.5;

// Interface / port parameters (mm)
port_uhv_gate_bonnet_cf63_od = 113.500;
port_uhv_gate_bonnet_cf63_bore = 63.500;
port_uhv_gate_bonnet_cf63_pcd = 92.100;
port_uhv_gate_bonnet_cf63_bolts = 8;
port_iso10156_vcr_in_od = 19.000;
port_iso10156_vcr_in_bore = 0.500;

module part_S7_SAFETY_06() {
  union() {
    // CF63 UHV gate-valve bonnet flange
    translate([-38.000, 0.000, -68.000]) {
      difference() {
        cylinder(d=113.500, h=17.500, center=true);
        cylinder(d=32.000, h=19.500, center=true);
        translate([0, 0, 7.500]) cylinder(d=82.400, h=1.750);
        for (i = [0 : 8 - 1])
          rotate([0, 0, i * 360 / 8])
            translate([46.050, 0, 0])
              cylinder(d=8.400, h=19.500, center=true);
      }
    }
    // Spring-return fail-close pneumatic cylinder
    translate([-38.000, 0.000, 14.000]) cylinder(d=84.000, h=146.000, center=true);
    // ISO 10156 5% H2/N2 flow-restrictor orifice block
    translate([68.000, 36.000, -35.000]) cube([68.000, 54.000, 44.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([660.000, -360.000, 440.000]) rotate([0.000, 0.000, 0.000]) part_S7_SAFETY_06();

part_S7_SAFETY_06();
