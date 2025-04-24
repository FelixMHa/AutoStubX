

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        String output_1 = input_1_0.toString();
        String output_2 = input_2_0.toString();

        
        // Compare output
        if (output_1.equals("2.3734802E7") && output_2.equals("3.5669795E22")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

