

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        String input_1_0 = String.valueOf(args[0]);
        String input_2_0 = String.valueOf(args[1]);


        // Perform computation         
        String output_1 = input_1_0.toLowerCase();
        String output_2 = input_2_0.toLowerCase();

        
        // Compare output
        if (output_1.equals("") && output_2.equals("|/")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

