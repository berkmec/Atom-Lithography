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
// envelope_mm       : 588.200 x 506.000 x 463.700
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 588.2000;
bbox_y = 506.0000;
bbox_z = 463.7000;

// Part-specific parametric dimensions
close_time_ms = 80.0;
bonnet_cf = "CF100";
bonnet_od_mm = 152.0;
bonnet_bore_mm = 68.0;
orifice_bore_mm = 0.5;

// Interface / port parameters (mm)
port_uhv_gate_bonnet_cf100_od = 152.000;
port_uhv_gate_bonnet_cf100_bore = 68.000;
port_uhv_gate_bonnet_cf100_pcd = 130.200;
port_uhv_gate_bonnet_cf100_bolts = 16;
port_iso10156_vcr_in_od = 19.000;
port_iso10156_vcr_in_bore = 0.500;

module part_S7_SAFETY_06() {
  union() {
    // CF100 UHV gate-valve bonnet flange
    translate([0.000, 0.000, -73.100]) {
      difference() {
        cylinder(d=152.000, h=19.800, center=true);
        cylinder(d=68.000, h=21.800, center=true);
        translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
        for (i = [0 : 16 - 1])
          rotate([0, 0, i * 360 / 16])
            translate([65.100, 0, 0])
              cylinder(d=8.400, h=21.800, center=true);
      }
    }
    // Spring-return fail-close pneumatic cylinder
    translate([0.000, 0.000, 10.000]) cylinder(d=84.000, h=146.000, center=true);
    // ISO 10156 5% H2/N2 flow-restrictor orifice block
    translate([456.000, -324.000, -341.700]) cube([68.000, 54.000, 44.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([272.000, 0.000, 746.700]) rotate([0.000, 0.000, 0.000]) part_S7_SAFETY_06();

part_S7_SAFETY_06();
