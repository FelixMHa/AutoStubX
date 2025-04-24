

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Boolean input_1_0 = Boolean.valueOf(args[0]);
        Boolean input_2_0 = Boolean.valueOf(args[1]);


        // Perform computation         
        String output_1 = input_1_0.toString();
        String output_2 = input_2_0.toString();

        
        // Compare output
        if (output_1.equals("false") && output_2.equals("true")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

