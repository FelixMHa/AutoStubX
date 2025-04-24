

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_2_0 = Short.valueOf(args[1]);


        // Perform computation         
        Double output_1 = input_1_0.doubleValue();
        Double output_2 = input_2_0.doubleValue();

        
        // Compare output
        if (output_1 == 685.0 && output_2 == -133.0) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

