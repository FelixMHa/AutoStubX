

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_2_0 = Short.valueOf(args[1]);


        // Perform computation         
        String output_1 = input_1_0.toString();
        String output_2 = input_2_0.toString();

        
        // Compare output
        if (output_1.equals("-30464") && output_2.equals("-727")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

